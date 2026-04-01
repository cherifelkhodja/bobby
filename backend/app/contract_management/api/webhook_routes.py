"""Webhook routes for BoondManager and YouSign."""

import json
import traceback

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contract_management.api.schemas import WebhookResponse
from app.contract_management.application.use_cases.create_contract_request import (
    CreateContractRequestUseCase,
)
from app.contract_management.domain.exceptions import WebhookDuplicateError
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
    WebhookEventRepository,
)
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger

logger = structlog.get_logger()

router = APIRouter(tags=["Webhooks"])


def _make_company_email_resolver(db):
    """Create a company email resolver closure bound to the given DB session."""
    async def resolver(company_id):
        from sqlalchemy import select as _sel
        from app.contract_management.infrastructure.models import ContractCompanyModel
        r = await db.execute(
            _sel(ContractCompanyModel.email_from, ContractCompanyModel.name)
            .where(ContractCompanyModel.id == company_id)
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

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository

    boond_client = BoondClient(settings)
    crm_service = BoondCrmAdapter(boond_client)
    user_repo = UserRepository(db)

    use_case = CreateContractRequestUseCase(
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
        result = await use_case.execute(payload)
        if result:
            # Explicit commit to ensure data is persisted
            await db.commit()
            logger.info(
                "webhook_boond_contract_created",
                reference=result.reference,
                cr_id=str(result.id),
                status=result.status.value,
                commercial_email=result.commercial_email,
                frontend_url=settings.frontend_url,
            )
            return WebhookResponse(
                status="ok",
                message=f"Contract request {result.reference} created",
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

    try:
        payload = await request.json()
    except Exception:
        logger.warning("yousign_webhook_invalid_json")
        return WebhookResponse(status="ok", message="Invalid JSON")

    # Verify webhook secret if configured
    webhook_secret = settings.YOUSIGN_WEBHOOK_SECRET
    if webhook_secret:
        # YouSign sends signature in header
        signature = request.headers.get("x-yousign-signature", "")
        if not signature:
            logger.warning("yousign_webhook_no_signature")
            return WebhookResponse(status="ok", message="Missing signature")

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

        await use_case.execute(procedure_id)

        audit_logger.log(
            AuditAction.CONTRACT_SIGNED,
            AuditResource.CONTRACT,
            details={"procedure_id": procedure_id},
        )

        return WebhookResponse(status="ok", message="Signature processed")
    except Exception as exc:
        logger.error("yousign_webhook_processing_error", error=str(exc))
        return WebhookResponse(status="ok", message="Processing error")
