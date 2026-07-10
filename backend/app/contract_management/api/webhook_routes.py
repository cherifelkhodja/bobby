"""Webhook routes for BoondManager and YouSign."""

import hashlib
import hmac
import json
import traceback

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contract_management.api.schemas import WebhookResponse
from app.contract_management.domain.exceptions import WebhookDuplicateError
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
    WebhookEventRepository,
)
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger

logger = structlog.get_logger()

router = APIRouter(tags=["Webhooks"])


def _verify_boond_webhook_token(request: Request, settings) -> None:
    """Vérifie le secret partagé des webhooks BoondManager.

    Si ``BOOND_WEBHOOK_SECRET`` est configuré, le header ``X-Webhook-Token``
    doit correspondre (comparaison à temps constant via ``hmac.compare_digest``) ;
    sinon la requête est rejetée en 401.

    Si le secret est vide, on laisse passer (rétrocompatibilité) avec un warning.

    # NEEDS-CONFIRMATION : BoondManager doit être configuré pour envoyer le
    # header ``X-Webhook-Token`` avec la valeur du secret partagé.
    """
    expected = getattr(settings, "BOOND_WEBHOOK_SECRET", "") or ""
    if not expected:
        logger.warning("boond_webhook_secret_not_configured")
        return

    provided = request.headers.get("X-Webhook-Token", "")
    if not provided or not hmac.compare_digest(provided, expected):
        logger.warning("boond_webhook_invalid_token")
        raise HTTPException(status_code=401, detail="Invalid webhook token")


def _make_company_email_resolver(db):
    """Create a company email resolver closure bound to the given DB session."""

    async def resolver(company_id):
        from sqlalchemy import select as _sel

        from app.contract_management.infrastructure.models import ContractCompanyModel

        r = await db.execute(
            _sel(ContractCompanyModel.email_from, ContractCompanyModel.name).where(
                ContractCompanyModel.id == company_id
            )
        )
        row = r.first()
        return (row.email_from, row.name) if row else (None, None)

    return resolver


@router.post(
    "/boondmanager/positioning-update",
    response_model=WebhookResponse,
    summary="Handle BoondManager positioning update webhook",
)
async def handle_boond_positioning_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle positioning update from BoondManager.

    Always returns 200 OK to prevent retries from Boond.
    """
    settings = get_settings()
    _verify_boond_webhook_token(request, settings)

    # Log raw body for debugging
    raw_body = await request.body()
    logger.info(
        "webhook_boond_received",
        content_type=request.headers.get("content-type", ""),
        body_length=len(raw_body),
        body_preview=raw_body[:500].decode("utf-8", errors="replace"),
    )

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.warning("webhook_invalid_json", raw=raw_body[:200].decode("utf-8", errors="replace"))
        return WebhookResponse(status="ok", message="Invalid JSON")

    logger.info(
        "webhook_boond_payload_parsed",
        payload_type=type(payload).__name__,
        payload_keys=list(payload.keys()) if isinstance(payload, dict) else f"list[{len(payload)}]",
    )

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT_REQUEST,
        details={"source": "boondmanager", "type": "positioning_update"},
    )

    cr_repo = ContractRequestRepository(db)
    webhook_repo = WebhookEventRepository(db)

    from app.infrastructure.email.sender import EmailService

    email_service = EmailService(settings)

    from app.contract_management.application.use_cases.create_purchase_order_request_from_positioning import (  # noqa: E501
        CreatePurchaseOrderRequestFromPositioningUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        FrameworkContractRepository,
        PurchaseOrderRequestRepository,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository,
    )

    boond_client = BoondClient(settings)
    crm_service = BoondCrmAdapter(boond_client)
    user_repo = UserRepository(db)

    # Le webhook positionnement crée désormais un BDC (verrouillé tant que le
    # consultant n'est pas une ressource rattachée à un contrat cadre actif).
    # Le contrat cadre est déclenché uniquement par candidate-state-update.
    use_case = CreatePurchaseOrderRequestFromPositioningUseCase(
        purchase_order_request_repository=PurchaseOrderRequestRepository(db),
        contract_request_repository=cr_repo,
        webhook_event_repository=webhook_repo,
        third_party_repository=ThirdPartyRepository(db),
        framework_contract_repository=FrameworkContractRepository(db),
        crm_service=crm_service,
        email_service=email_service,
        user_repository=user_repo,
        frontend_url=settings.frontend_url,
        company_email_resolver=_make_company_email_resolver(db),
    )

    try:
        result = await use_case.execute(payload)
        if result:
            # Explicit commit to ensure data is persisted
            await db.commit()
            logger.info(
                "webhook_boond_bdc_created",
                reference=result.reference,
                por_id=str(result.id),
                status=result.status.value,
                commercial_email=result.commercial_email,
            )
            return WebhookResponse(
                status="ok",
                message=f"Purchase order request {result.reference} created",
            )
        logger.info("webhook_boond_no_action", reason="filtered_or_empty")
        return WebhookResponse(status="ok", message="No action taken")
    except WebhookDuplicateError as exc:
        logger.info("webhook_boond_duplicate", event_id=str(exc))
        return WebhookResponse(status="ok", message="Duplicate event")
    except Exception as exc:
        await db.rollback()
        logger.error(
            "webhook_processing_error",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return WebhookResponse(status="ok", message="Processing error")


@router.post(
    "/boondmanager/candidate-state-update",
    response_model=WebhookResponse,
    summary="Handle BoondManager candidate state update webhook",
)
async def handle_boond_candidate_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle candidate state update from BoondManager.

    Triggers contract request creation when candidate moves to state 11
    (En attente de contrat).

    Always returns 200 OK to prevent retries from Boond.
    """
    settings = get_settings()
    _verify_boond_webhook_token(request, settings)

    raw_body = await request.body()
    logger.info(
        "webhook_boond_candidate_received",
        body_length=len(raw_body),
        body_preview=raw_body[:500].decode("utf-8", errors="replace"),
    )

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.warning("webhook_invalid_json")
        return WebhookResponse(status="ok", message="Invalid JSON")

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT_REQUEST,
        details={"source": "boondmanager", "type": "candidate_state_update"},
    )

    cr_repo = ContractRequestRepository(db)
    webhook_repo = WebhookEventRepository(db)

    from app.contract_management.application.use_cases.create_contract_request_from_entity import (
        BOOND_CANDIDATE_STATE_AWAITING_CONTRACT,
        CreateContractRequestFromEntityUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository
    from app.infrastructure.email.sender import EmailService

    boond_client = BoondClient(settings)
    crm_service = BoondCrmAdapter(boond_client)
    email_service = EmailService(settings)
    user_repo = UserRepository(db)

    use_case = CreateContractRequestFromEntityUseCase(
        contract_request_repository=cr_repo,
        webhook_event_repository=webhook_repo,
        crm_service=crm_service,
        email_service=email_service,
        user_repository=user_repo,
        frontend_url=settings.frontend_url,
        company_repository=cr_repo,
        company_email_resolver=_make_company_email_resolver(db),
    )

    try:
        result = await use_case.execute(
            payload=payload,
            entity_type="candidate",
            expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
        )
        if result:
            await db.commit()
            logger.info(
                "webhook_candidate_contract_created",
                cr_id=str(result.id),
                reference=result.display_reference,
            )
            return WebhookResponse(
                status="ok",
                message=f"Contract request {result.display_reference} created from candidate",
            )
        return WebhookResponse(status="ok", message="No action taken")
    except WebhookDuplicateError as exc:
        logger.info("webhook_candidate_duplicate", event_id=str(exc))
        return WebhookResponse(status="ok", message="Duplicate event")
    except Exception as exc:
        await db.rollback()
        logger.error(
            "webhook_candidate_processing_error",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return WebhookResponse(status="ok", message="Processing error")


@router.post(
    "/boondmanager/resource-state-update",
    response_model=WebhookResponse,
    summary="Handle BoondManager resource state update webhook",
)
async def handle_boond_resource_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle resource state update from BoondManager.

    Triggers contract request creation when resource moves to:
    - State 4 (Attente nouveau contrat): re-contractualization (expired contract)
    - State 5 (Changement de contrat): new company, full workflow

    Always returns 200 OK to prevent retries from Boond.
    """
    settings = get_settings()
    _verify_boond_webhook_token(request, settings)

    raw_body = await request.body()
    logger.info(
        "webhook_boond_resource_received",
        body_length=len(raw_body),
        body_preview=raw_body[:500].decode("utf-8", errors="replace"),
    )

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.warning("webhook_invalid_json")
        return WebhookResponse(status="ok", message="Invalid JSON")

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT_REQUEST,
        details={"source": "boondmanager", "type": "resource_state_update"},
    )

    cr_repo = ContractRequestRepository(db)
    webhook_repo = WebhookEventRepository(db)

    from app.contract_management.application.use_cases.create_contract_request_from_entity import (
        BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
        BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
        CreateContractRequestFromEntityUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository
    from app.infrastructure.email.sender import EmailService

    boond_client = BoondClient(settings)
    crm_service = BoondCrmAdapter(boond_client)
    email_service = EmailService(settings)
    user_repo = UserRepository(db)

    use_case = CreateContractRequestFromEntityUseCase(
        contract_request_repository=cr_repo,
        webhook_event_repository=webhook_repo,
        crm_service=crm_service,
        email_service=email_service,
        user_repository=user_repo,
        frontend_url=settings.frontend_url,
        company_repository=cr_repo,
        company_email_resolver=_make_company_email_resolver(db),
    )

    try:
        result = await use_case.execute(
            payload=payload,
            entity_type="resource",
            expected_states=[
                BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
                BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
            ],
        )
        if result:
            await db.commit()
            logger.info(
                "webhook_resource_contract_created",
                cr_id=str(result.id),
                reference=result.display_reference,
                trigger_type=result.trigger_type,
            )
            return WebhookResponse(
                status="ok",
                message=f"Contract request {result.display_reference} created from resource",
            )
        return WebhookResponse(status="ok", message="No action taken")
    except WebhookDuplicateError as exc:
        logger.info("webhook_resource_duplicate", event_id=str(exc))
        return WebhookResponse(status="ok", message="Duplicate event")
    except Exception as exc:
        await db.rollback()
        logger.error(
            "webhook_resource_processing_error",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return WebhookResponse(status="ok", message="Processing error")


@router.post(
    "/boondmanager/test",
    summary="Test endpoint - capture any Boond webhook payload",
)
async def test_boond_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Capture and store any Boond webhook payload for inspection.

    Stores the payload in cm_webhook_events with event_type='debug_capture'.
    Use GET /boondmanager/debug-webhooks to retrieve captured payloads.
    Not available in production.
    """
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except Exception:
        payload = {"raw": raw_body.decode("utf-8", errors="replace")}

    # Store in DB for later inspection
    from datetime import datetime

    webhook_repo = WebhookEventRepository(db)
    event_id = f"debug_{datetime.utcnow().isoformat()}"
    await webhook_repo.save(
        event_id=event_id,
        event_type="debug_capture",
        payload=payload if isinstance(payload, dict) else {"data": payload},
    )
    await db.commit()

    return {
        "status": "ok",
        "message": "Webhook captured and stored",
        "event_id": event_id,
        "headers": {
            k: v
            for k, v in request.headers.items()
            if k.lower() in ("content-type", "user-agent", "x-forwarded-for", "host")
        },
        "body_length": len(raw_body),
        "payload": payload,
    }


@router.get(
    "/boondmanager/debug-webhooks",
    summary="Debug: list captured webhook payloads",
)
async def debug_list_webhooks(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """List recently captured webhook payloads. Not available in production."""
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import WebhookEventModel

    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    result = await db.execute(
        select(WebhookEventModel)
        .where(WebhookEventModel.event_type == "debug_capture")
        .order_by(WebhookEventModel.processed_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "status": "ok",
        "total": len(events),
        "webhooks": [
            {
                "event_id": e.event_id,
                "payload": e.payload,
                "received_at": e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in events
        ],
    }


@router.get(
    "/boondmanager/debug-resource/{resource_id}",
    summary="Debug: dump a Boond resource administrative payload",
)
async def debug_resource_provider(resource_id: int):
    """Dump the administrative + base payload of a Boond resource.

    Helps confirm the ``providerCompany`` relationship (name + endpoint) used to
    link a consultant to its supplier for the BDC flow. Not available in
    production.
    """
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient

    boond_client = BoondClient(settings)
    crm = BoondCrmAdapter(boond_client)

    result: dict = {"status": "ok", "resource_id": resource_id, "endpoints": {}}

    for endpoint in (
        f"/resources/{resource_id}/administrative",
        f"/resources/{resource_id}",
    ):
        try:
            response = await boond_client._make_request("GET", endpoint)
            data = response.get("data", {})
            relationships = data.get("relationships", {})
            result["endpoints"][endpoint] = {
                "relationship_keys": list(relationships.keys()),
                "providerCompany": relationships.get("providerCompany"),
            }
        except Exception as exc:  # noqa: BLE001
            result["endpoints"][endpoint] = {"error": str(exc)}

    # Resolved value via the adapter helper (what the BDC flow actually uses)
    result["resolved_provider_company_id"] = await crm.get_resource_provider_company_id(
        resource_id
    )
    return result


@router.get(
    "/boondmanager/debug-positioning/{positioning_id}",
    summary="Debug: dump a Boond positioning payload (fields for BDC)",
)
async def debug_positioning(positioning_id: int):
    """Dump the raw + parsed positioning payload used to pre-fill a BDC.

    Lets us confirm the exact Boond attribute keys for TJM (tarif de vente),
    billed days, dates and consultant. Not available in production.
    """
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient

    boond_client = BoondClient(settings)
    crm = BoondCrmAdapter(boond_client)

    raw_attributes: dict = {}
    try:
        response = await boond_client._make_request("GET", f"/positionings/{positioning_id}")
        raw_attributes = response.get("data", {}).get("attributes", {})
    except Exception as exc:  # noqa: BLE001
        raw_attributes = {"error": str(exc)}

    parsed = await crm.get_positioning(positioning_id)

    return {
        "status": "ok",
        "positioning_id": positioning_id,
        "raw_attributes": raw_attributes,
        "parsed_for_bdc": parsed,
    }


@router.get(
    "/boondmanager/debug-bdc-detection/{positioning_id}",
    summary="Debug: trace the BDC lock/unlock detection chain",
)
async def debug_bdc_detection(positioning_id: int, db: AsyncSession = Depends(get_db)):
    """Run the full 'resource + active framework contract' detection for a
    positioning and report each step. Explains why a BDC is locked or editable.
    Not available in production.
    """
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        FrameworkContractRepository,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository,
    )

    crm = BoondCrmAdapter(BoondClient(settings))
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)
    fc_repo = FrameworkContractRepository(db)

    steps: dict = {}

    positioning = await crm.get_positioning(positioning_id)
    if not positioning:
        return {"status": "error", "message": "positioning introuvable", "steps": steps}

    consultant_type = positioning.get("consultant_type")
    candidate_id = positioning.get("candidate_id")
    need_id = positioning.get("need_id")
    steps["1_positioning"] = {
        "state": positioning.get("state"),
        "consultant_type": consultant_type,
        "candidate_id": candidate_id,
        "need_id": need_id,
    }

    # Resolve resource id (even if the positioning still references a candidate)
    resource_id = candidate_id if consultant_type == "resource" else None
    resolved_resource = None
    if consultant_type != "resource" and candidate_id:
        resolved_resource = await crm.resolve_resource_id(candidate_id)
    steps["2_resource_id"] = {
        "used_resource_id": resource_id,
        "candidate_maps_to_resource": resolved_resource,
    }

    lookup_resource_id = resource_id or resolved_resource
    provider_company_id = None
    if lookup_resource_id:
        provider_company_id = await crm.get_resource_provider_company_id(lookup_resource_id)
    steps["3_provider_company_id"] = provider_company_id

    tp = None
    if provider_company_id:
        tp = await tp_repo.get_by_boond_provider_id(provider_company_id)
    steps["4_third_party"] = (
        {"id": str(tp.id), "company_name": tp.company_name} if tp else None
    )

    company_id = None
    if need_id:
        need = await crm.get_need(need_id)
        agency_id = need.get("agency_id") if need else None
        if agency_id:
            company_id = await cr_repo.get_company_by_boond_agency_id(agency_id)
    steps["5_company_id"] = str(company_id) if company_id else None

    fc = None
    if tp:
        fc = await fc_repo.get_active_by_third_party(tp.id, company_id)
    steps["6_active_framework_contract"] = (
        {"id": str(fc.id), "reference": fc.reference, "status": fc.status.value} if fc else None
    )

    editable = fc is not None
    return {
        "status": "ok",
        "positioning_id": positioning_id,
        "verdict": "EDITABLE (rattaché à un contrat cadre actif)"
        if editable
        else "VERROUILLE (pas de ressource+contrat cadre actif détecté)",
        "steps": steps,
    }


@router.get(
    "/boondmanager/debug-cr",
    summary="Debug: check contract requests in DB",
)
async def debug_contract_requests(
    db: AsyncSession = Depends(get_db),
):
    """List recent contract requests for debugging. Not available in production."""
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    cr_repo = ContractRequestRepository(db)
    items = await cr_repo.list_all(skip=0, limit=10)

    return {
        "status": "ok",
        "total": len(items),
        "contract_requests": [
            {
                "id": str(cr.id),
                "reference": cr.display_reference,
                "status": cr.status.value,
                "boond_positioning_id": cr.boond_positioning_id,
                "commercial_email": cr.commercial_email,
                "client_name": cr.client_name,
                "created_at": str(cr.created_at) if cr.created_at else None,
            }
            for cr in items
        ],
        "email_config": {
            "feature_enabled": settings.FEATURE_EMAIL_NOTIFICATIONS,
            "has_resend_key": bool(settings.RESEND_API_KEY),
            "smtp_host": settings.SMTP_HOST,
            "from_email": settings.SMTP_FROM,
            "frontend_url": settings.frontend_url,
        },
    }


@router.post(
    "/yousign/signature-completed",
    response_model=WebhookResponse,
    summary="Handle YouSign signature completed webhook",
)
async def handle_yousign_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle signature completed event from YouSign."""
    settings = get_settings()

    # On lit le corps brut pour vérifier la signature HMAC AVANT de parser.
    raw_body = await request.body()

    # Vraie vérification HMAC : hmac.new(secret, raw_body, sha256) comparé
    # au header via compare_digest. Secret vide → warning + on laisse passer.
    webhook_secret = settings.YOUSIGN_WEBHOOK_SECRET
    if webhook_secret:
        signature = request.headers.get("x-yousign-signature", "")
        # YouSign peut préfixer la signature par "sha256=".
        if signature.startswith("sha256="):
            signature = signature[len("sha256=") :]
        expected = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            logger.warning("yousign_webhook_invalid_signature")
            return WebhookResponse(status="ok", message="Invalid signature")
    else:
        logger.warning("yousign_webhook_secret_not_configured")

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.warning("yousign_webhook_invalid_json")
        return WebhookResponse(status="ok", message="Invalid JSON")

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT,
        details={"source": "yousign", "type": "signature_completed"},
    )

    event_type = payload.get("event_name", "")
    if event_type != "signature_request.done":
        return WebhookResponse(status="ok", message=f"Ignored event: {event_type}")

    procedure_id = payload.get("data", {}).get("signature_request", {}).get("id", "")
    if not procedure_id:
        logger.warning("yousign_webhook_no_procedure_id")
        return WebhookResponse(status="ok", message="No procedure ID")

    logger.info(
        "yousign_signature_completed",
        procedure_id=procedure_id,
    )

    # Process signature completion
    try:
        from app.contract_management.application.use_cases.handle_signature_completed import (
            HandleSignatureCompletedUseCase,
        )
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            ContractRepository,
        )
        from app.contract_management.infrastructure.adapters.yousign_client import YouSignClient
        from app.infrastructure.email.sender import EmailService
        from app.infrastructure.storage.s3_client import S3StorageClient

        cr_repo = ContractRequestRepository(db)
        contract_repo = ContractRepository(db)
        yousign = YouSignClient(
            api_key=settings.YOUSIGN_API_KEY,
            base_url=settings.YOUSIGN_API_BASE_URL,
        )
        s3_service = S3StorageClient(settings)
        email_service = EmailService(settings)

        use_case = HandleSignatureCompletedUseCase(
            contract_request_repository=cr_repo,
            contract_repository=contract_repo,
            signature_service=yousign,
            s3_service=s3_service,
            email_service=email_service,
            company_email_resolver=_make_company_email_resolver(db),
        )

        # Résolution procédure YouSign → contrat. Le repository n'expose pas de
        # finder dédié (fichier hors périmètre modifiable), on interroge donc le
        # modèle directement, comme le fait déjà le flux manuel mark-as-signed.
        from sqlalchemy import select

        from app.contract_management.infrastructure.models import ContractModel

        result = await db.execute(
            select(ContractModel.id)
            .where(ContractModel.yousign_procedure_id == procedure_id)
            .limit(1)
        )
        contract_id = result.scalar_one_or_none()
        if not contract_id:
            # Aucun contrat associé à cette procédure. En l'état, le flux auto
            # n'assigne pas encore yousign_procedure_id (cf. send_for_signature,
            # # NEEDS-CONFIRMATION) : ce webhook reste donc un no-op sûr.
            logger.warning("yousign_webhook_no_matching_contract", procedure_id=procedure_id)
            return WebhookResponse(status="ok", message="No matching contract")

        # Idempotent : no-op si déjà SIGNED (ne casse pas mark-as-signed manuel).
        await use_case.execute_for_contract(contract_id)
        await db.commit()

        audit_logger.log(
            AuditAction.CONTRACT_SIGNED,
            AuditResource.CONTRACT,
            details={"procedure_id": procedure_id},
        )

        return WebhookResponse(status="ok", message="Signature processed")
    except Exception as exc:
        await db.rollback()
        logger.error("yousign_webhook_processing_error", error=str(exc))
        return WebhookResponse(status="ok", message="Processing error")
