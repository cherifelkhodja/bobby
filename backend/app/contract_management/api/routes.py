"""Contract management API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser, ContractAccessUser
from app.config import get_settings
from app.contract_management.api.schemas import (
    ArticleOverridesRequest,
    CommercialValidationRequest,
    ComplianceOverrideRequest,
    ContractConfigRequest,
    ContractRequestListResponse,
    ContractRequestResponse,
    ContractResponse,
)
from app.contract_management.application.use_cases.block_compliance import (
    BlockComplianceUseCase,
)
from app.contract_management.application.use_cases.configure_contract import (
    ConfigureContractUseCase,
)
from app.contract_management.application.use_cases.start_compliance_review import (
    StartComplianceReviewUseCase,
)
from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
    ValidateCommercialUseCase,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
)
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.infrastructure.database.models import UserModel
from app.third_party.application.use_cases.generate_magic_link import (
    GenerateMagicLinkUseCase,
)
from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
    MagicLinkRepository,
)
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)
from app.vigilance.application.use_cases.request_documents import RequestDocumentsUseCase
from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository

logger = structlog.get_logger()

router = APIRouter(tags=["Contract Management"])


async def _notify_commercial(
    email_service,
    *,
    to: str,
    ref: str,
    title: str,
    msg: str,
    color: str = "#0ea5e9",
) -> None:
    """Fire-and-forget contract progress notification to the commercial."""
    try:
        await email_service.send_contract_progress_to_commercial(
            to=to,
            contract_ref=ref,
            step_title=title,
            step_message=msg,
            step_color=color,
        )
    except Exception as exc:
        logger.warning("commercial_notification_failed", error=str(exc), to=to)


async def _resolve_commercial_name(db: AsyncSession, email: str) -> str | None:
    """Resolve a commercial email to full name from users table."""
    from sqlalchemy import select

    stmt = select(UserModel.first_name, UserModel.last_name).where(UserModel.email == email)
    row = (await db.execute(stmt)).first()
    if row:
        return f"{row.first_name} {row.last_name}".strip()
    return None


async def _resolve_commercial_names(db: AsyncSession, emails: list[str]) -> dict[str, str]:
    """Resolve commercial emails to full names from users table."""
    if not emails:
        return {}
    from sqlalchemy import select

    stmt = select(UserModel.email, UserModel.first_name, UserModel.last_name).where(
        UserModel.email.in_(emails)
    )
    result = await db.execute(stmt)
    return {row.email: f"{row.first_name} {row.last_name}".strip() for row in result.all()}


def _cr_to_response(
    cr,
    *,
    commercial_name: str | None = None,
    portal_url: str | None = None,
) -> ContractRequestResponse:
    """Convert a ContractRequest entity to response."""
    return ContractRequestResponse(
        id=cr.id,
        reference=cr.reference,
        boond_positioning_id=cr.boond_positioning_id,
        status=cr.status.value,
        status_display=cr.status.display_name,
        third_party_type=cr.third_party_type,
        daily_rate=float(cr.daily_rate) if cr.daily_rate else None,
        start_date=cr.start_date,
        end_date=cr.end_date,
        client_name=cr.client_name,
        mission_title=cr.mission_title,
        mission_description=cr.mission_description,
        consultant_civility=cr.consultant_civility,
        consultant_first_name=cr.consultant_first_name,
        consultant_last_name=cr.consultant_last_name,
        consultant_email=cr.consultant_email,
        consultant_phone=cr.consultant_phone,
        mission_site_name=cr.mission_site_name,
        mission_address=cr.mission_address,
        mission_postal_code=cr.mission_postal_code,
        mission_city=cr.mission_city,
        commercial_email=cr.commercial_email,
        commercial_name=commercial_name,
        contractualization_contact_email=cr.contractualization_contact_email,
        third_party_id=cr.third_party_id,
        portal_url=portal_url,
        compliance_override=cr.compliance_override,
        contract_config=cr.contract_config,
        status_history=cr.status_history or [],
        created_at=cr.created_at,
        updated_at=cr.updated_at,
    )


@router.get(
    "",
    response_model=ContractRequestListResponse,
    summary="List contract requests",
)
async def list_contract_requests(
    auth: ContractAccessUser,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List contract requests. Commercial sees own, ADV/admin see all."""
    _user_id, role, email = auth
    cr_repo = ContractRequestRepository(db)

    status_obj = None
    if status_filter:
        try:
            status_obj = ContractRequestStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut invalide : {status_filter}",
            )

    if role == "commercial":
        items = await cr_repo.list_by_commercial_email(
            email, skip=skip, limit=limit, status=status_obj
        )
        total = await cr_repo.count_by_commercial_email(email, status=status_obj)
    else:
        items = await cr_repo.list_all(skip=skip, limit=limit, status=status_obj)
        total = await cr_repo.count(status=status_obj)

    emails = list({cr.commercial_email for cr in items})
    name_map = await _resolve_commercial_names(db, emails)

    return ContractRequestListResponse(
        items=[
            _cr_to_response(cr, commercial_name=name_map.get(cr.commercial_email)) for cr in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{contract_request_id}",
    response_model=ContractRequestResponse,
    summary="Get contract request details",
)
async def get_contract_request(
    contract_request_id: UUID,
    auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a contract request by ID. Commercial sees own, ADV/admin see all."""
    from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

    _user_id, role, email = auth
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    # Resolve active portal URL if a third party is linked
    portal_url: str | None = None
    if cr.third_party_id:
        ml_repo = MagicLinkRepository(db)
        active_link = await ml_repo.get_active_by_third_party_and_purpose(
            cr.third_party_id, MagicLinkPurpose.DOCUMENT_UPLOAD
        )
        if active_link:
            settings = get_settings()
            portal_url = f"{settings.BOBBY_PORTAL_BASE_URL}/{active_link.token}"

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name, portal_url=portal_url)


@router.post(
    "/{contract_request_id}/sync-from-boond",
    response_model=ContractRequestResponse,
    summary="Re-sync contract request data from BoondManager",
)
async def sync_from_boond(
    contract_request_id: UUID,
    auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """Re-fetch positioning and need data from Boond to update the CR.

    Useful for CRs created before fields were added, or when Boond data
    was incomplete at webhook time.
    """
    _user_id, role, email = auth
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    settings = get_settings()

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient

    boond_client = BoondClient(settings)
    crm = BoondCrmAdapter(boond_client)

    # Fetch positioning data
    positioning_data = await crm.get_positioning(cr.boond_positioning_id)
    if not positioning_data:
        raise HTTPException(
            status_code=502,
            detail="Impossible de récupérer les données du positionnement Boond.",
        )

    from datetime import date
    from decimal import Decimal, InvalidOperation

    def _parse_date(raw: object) -> date | None:
        if raw and isinstance(raw, str):
            try:
                return date.fromisoformat(raw[:10])
            except (ValueError, TypeError):
                return None
        if isinstance(raw, date):
            return raw
        return None

    raw_daily_rate = positioning_data.get("daily_rate")
    if raw_daily_rate:
        try:
            cr.daily_rate = Decimal(str(raw_daily_rate))
        except (InvalidOperation, ValueError, TypeError):
            pass

    raw_start = positioning_data.get("start_date")
    parsed_start = _parse_date(raw_start)
    if parsed_start:
        cr.start_date = parsed_start

    raw_end = positioning_data.get("end_date")
    parsed_end = _parse_date(raw_end)
    if parsed_end:
        cr.end_date = parsed_end

    # Update consultant info from positioning included data
    consultant_fn = positioning_data.get("consultant_first_name")
    consultant_ln = positioning_data.get("consultant_last_name")
    if consultant_fn:
        cr.consultant_first_name = consultant_fn
    if consultant_ln:
        cr.consultant_last_name = consultant_ln

    # Fetch need data
    need_id = positioning_data.get("need_id") or cr.boond_need_id
    if need_id:
        need_data = await crm.get_need(need_id)
        if need_data:
            client_name = need_data.get("client_name")
            if client_name:
                cr.client_name = client_name
            title = need_data.get("title")
            if title:
                cr.mission_title = title
            description = need_data.get("description")
            if description:
                cr.mission_description = description
            if not cr.boond_need_id and need_id:
                cr.boond_need_id = need_id

    # Sync consultant info from positioning candidate
    candidate_id = positioning_data.get("candidate_id")
    if candidate_id:
        candidate_info = await crm.get_candidate_info(candidate_id)
        if candidate_info:
            cr.consultant_civility = candidate_info.get("civility") or None
            cr.consultant_first_name = candidate_info.get("first_name") or None
            cr.consultant_last_name = candidate_info.get("last_name") or None
            cr.consultant_email = candidate_info.get("email") or None

    saved = await cr_repo.save(cr)
    await db.commit()

    logger.info(
        "contract_request_synced_from_boond",
        cr_id=str(saved.id),
        positioning_id=cr.boond_positioning_id,
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


@router.post(
    "/{contract_request_id}/validate-commercial",
    response_model=ContractRequestResponse,
    summary="Validate commercial information",
)
async def validate_commercial(
    contract_request_id: UUID,
    body: CommercialValidationRequest,
    access: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """Apply commercial validation to a contract request. Commercial/ADV/admin."""
    from app.infrastructure.email.sender import EmailService

    user_id, _role, _email = access
    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)
    ml_repo = MagicLinkRepository(db)
    doc_repo = DocumentRepository(db)

    email_service = EmailService(settings)
    generate_magic_link_uc = GenerateMagicLinkUseCase(
        third_party_repository=tp_repo,
        magic_link_repository=ml_repo,
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
    )
    request_documents_uc = RequestDocumentsUseCase(
        third_party_repository=tp_repo,
        document_repository=doc_repo,
    )

    use_case = ValidateCommercialUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        find_or_create_third_party_use_case=None,
        generate_magic_link_use_case=generate_magic_link_uc,
        request_documents_use_case=request_documents_uc,
    )

    try:
        cr = await use_case.execute(
            ValidateCommercialCommand(
                contract_request_id=contract_request_id,
                third_party_type=body.third_party_type,
                daily_rate=body.daily_rate,
                start_date=body.start_date,
                end_date=body.end_date,
                contact_email=body.contact_email,
                client_name=body.client_name,
                mission_title=body.mission_title,
                mission_description=body.mission_description,
                consultant_civility=body.consultant_civility,
                consultant_first_name=body.consultant_first_name,
                consultant_last_name=body.consultant_last_name,
                consultant_email=body.consultant_email,
                consultant_phone=body.consultant_phone,
                mission_site_name=body.mission_site_name,
                mission_address=body.mission_address,
                mission_postal_code=body.mission_postal_code,
                mission_city=body.mission_city,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.COMMERCIAL_VALIDATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
    )

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    if cr.status == ContractRequestStatus.COLLECTING_DOCUMENTS:
        await _notify_commercial(
            email_service,
            to=cr.commercial_email,
            ref=cr.reference,
            title="Collecte de documents lancée",
            msg=f"Votre validation commerciale a été enregistrée{client_label}. Le tiers a été contacté pour fournir ses documents légaux.",
        )
    elif cr.status == ContractRequestStatus.REDIRECTED_PAYFIT:
        await _notify_commercial(
            email_service,
            to=cr.commercial_email,
            ref=cr.reference,
            title="Dossier redirigé vers PayFit",
            msg=f"Ce consultant étant salarié{client_label}, la contractualisation sera gérée via PayFit.",
            color="#f59e0b",
        )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/resend-collection-email",
    response_model=ContractRequestResponse,
    summary="Resend the document collection magic link to the third party",
)
async def resend_collection_email(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new magic link and resend the collection email to the tiers.
    Can be called when status is COLLECTING_DOCUMENTS or COMPLIANCE_BLOCKED.
    ADV/admin only.
    """
    from app.contract_management.domain.value_objects.contract_request_status import (
        ContractRequestStatus as CRStatus,
    )
    from app.infrastructure.email.sender import EmailService
    from app.third_party.application.use_cases.generate_magic_link import (
        GenerateMagicLinkCommand,
        GenerateMagicLinkUseCase,
    )
    from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
    from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
        MagicLinkRepository,
    )

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    allowed = {CRStatus.COLLECTING_DOCUMENTS, CRStatus.REVIEWING_COMPLIANCE, CRStatus.COMPLIANCE_BLOCKED}
    if cr.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Le renvoi du lien n'est possible qu'en cours de collecte, vérification ou en conformité bloquée.",
        )

    if not cr.third_party_id or not cr.contractualization_contact_email:
        raise HTTPException(
            status_code=400,
            detail="Aucun tiers ou email de contact associé à cette demande.",
        )

    settings = get_settings()
    tp_repo = ThirdPartyRepository(db)
    ml_repo = MagicLinkRepository(db)
    email_service = EmailService(settings)

    generate_magic_link_uc = GenerateMagicLinkUseCase(
        third_party_repository=tp_repo,
        magic_link_repository=ml_repo,
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
    )

    try:
        await generate_magic_link_uc.execute(
            GenerateMagicLinkCommand(
                third_party_id=cr.third_party_id,
                purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
                email=cr.contractualization_contact_email,
                contract_request_id=cr.id,
            )
        )
    except Exception as exc:
        logger.error("resend_collection_email_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.DOCUMENT_COLLECTION_INITIATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "resend_collection_email"},
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/configure",
    response_model=ContractRequestResponse,
    summary="Configure contract details",
)
async def configure_contract(
    contract_request_id: UUID,
    body: ContractConfigRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Set contract configuration. ADV/admin only."""
    cr_repo = ContractRequestRepository(db)

    use_case = ConfigureContractUseCase(contract_request_repository=cr_repo)

    try:
        cr = await use_case.execute(contract_request_id, body.model_dump(mode='json'))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.patch(
    "/{contract_request_id}/article-overrides",
    response_model=ContractRequestResponse,
    summary="Save per-contract article/annex content overrides",
)
async def save_article_overrides(
    contract_request_id: UUID,
    body: ArticleOverridesRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Persist per-contract article and annex overrides into contract_config.

    Merges the provided overrides dict into the existing contract_config so
    other config fields (payment_terms, etc.) are preserved.
    Empty string values remove the override (restores template default).
    ADV/admin only.
    """
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    cfg = dict(cr.contract_config or {})

    # Merge article overrides — remove keys with empty values (reset to template)
    existing_article = dict(cfg.get("article_overrides") or {})
    for key, value in body.article_overrides.items():
        if value.strip():
            existing_article[key] = value
        else:
            existing_article.pop(key, None)
    cfg["article_overrides"] = existing_article

    # Merge annex overrides — same logic
    existing_annex = dict(cfg.get("annex_overrides") or {})
    for key, value in body.annex_overrides.items():
        if value.strip():
            existing_annex[key] = value
        else:
            existing_annex.pop(key, None)
    cfg["annex_overrides"] = existing_annex

    # Merge deleted keys — None means "no change", [] means "restore all"
    if body.deleted_article_keys is not None:
        cfg["deleted_article_keys"] = list(set(body.deleted_article_keys))
    if body.deleted_annex_keys is not None:
        cfg["deleted_annex_keys"] = list(set(body.deleted_annex_keys))

    cr.contract_config = cfg
    saved = await cr_repo.save(cr)

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


@router.post(
    "/{contract_request_id}/compliance-override",
    response_model=ContractRequestResponse,
    summary="Override compliance check",
)
async def compliance_override(
    contract_request_id: UUID,
    body: ComplianceOverrideRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Override compliance check for a contract request. ADV/admin only."""
    cr_repo = ContractRequestRepository(db)

    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    cr.override_compliance(body.reason)
    saved = await cr_repo.save(cr)

    audit_logger.log(
        AuditAction.COMPLIANCE_OVERRIDDEN,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"reason": body.reason},
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


@router.post(
    "/{contract_request_id}/start-compliance-review",
    response_model=ContractRequestResponse,
    summary="Start compliance review",
)
async def start_compliance_review(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Manually transition to REVIEWING_COMPLIANCE. ADV/admin only.

    Used when ADV wants to start reviewing documents without waiting for
    the third party to click 'Valider le dépôt' on the portal.
    """
    cr_repo = ContractRequestRepository(db)
    use_case = StartComplianceReviewUseCase(contract_request_repository=cr_repo)

    try:
        cr = await use_case.execute(contract_request_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.COMPLIANCE_OVERRIDDEN,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "start_compliance_review"},
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/block-compliance",
    response_model=ContractRequestResponse,
    summary="Block compliance",
)
async def block_compliance(
    contract_request_id: UUID,
    body: ComplianceOverrideRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Transition from REVIEWING_COMPLIANCE to COMPLIANCE_BLOCKED. ADV/admin only.

    Called when documents are deemed non-conformant after review.
    """
    cr_repo = ContractRequestRepository(db)
    use_case = BlockComplianceUseCase(contract_request_repository=cr_repo)

    try:
        cr = await use_case.execute(contract_request_id, body.reason)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.COMPLIANCE_OVERRIDDEN,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "block_compliance", "reason": body.reason},
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.delete(
    "/{contract_request_id}",
    response_model=ContractRequestResponse,
    summary="Cancel a contract request",
)
async def cancel_contract_request(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a contract request. ADV/admin only.

    Only allowed when the Boond positioning state is no longer 7 or 2.
    """
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.email.sender import EmailService

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if not cr.can_transition_to(ContractRequestStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'annuler une demande au statut '{cr.status.display_name}'.",
        )

    # Check Boond positioning state — only allow cancel if state is NOT 7 or 2
    boond_crm = BoondCrmAdapter(BoondClient(settings))
    positioning = await boond_crm.get_positioning(cr.boond_positioning_id)
    if not positioning:
        raise HTTPException(
            status_code=502,
            detail="Impossible de récupérer le positionnement depuis BoondManager.",
        )

    boond_state = positioning.get("state")
    BLOCKED_STATES = {
        2: "Gagné",
        7: "Gagné attente contrat",
    }
    if boond_state in BLOCKED_STATES:
        label = BLOCKED_STATES[boond_state]
        raise HTTPException(
            status_code=400,
            detail=f"Annulation impossible : le positionnement Boond est en état « {label} » ({boond_state}).",
        )

    previous_status = cr.status.value
    cr.transition_to(ContractRequestStatus.CANCELLED)
    saved = await cr_repo.save(cr)

    # Remove webhook dedup entries so a new webhook can re-create a CR
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        WebhookEventRepository,
    )

    webhook_repo = WebhookEventRepository(db)
    deleted = await webhook_repo.delete_by_prefix(f"positioning_update_{cr.boond_positioning_id}_")

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CANCELLED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={
            "previous_status": previous_status,
            "boond_positioning_state": boond_state,
        },
    )

    logger.info(
        "contract_request_cancelled",
        cr_id=str(contract_request_id),
        reference=saved.reference,
        boond_state=boond_state,
        webhook_events_cleared=deleted,
    )

    client_label = f" pour <strong>{saved.client_name}</strong>" if saved.client_name else ""
    await _notify_commercial(
        EmailService(settings),
        to=saved.commercial_email,
        ref=saved.reference,
        title="Demande de contrat annulée",
        msg=f"La demande de contrat{client_label} a été annulée (statut précédent : {previous_status}).",
        color="#ef4444",
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


@router.get(
    "/next-reference",
    summary="Get next contract request reference",
)
async def get_next_reference(
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get the next available contract request reference. ADV/admin only."""
    cr_repo = ContractRequestRepository(db)
    reference = await cr_repo.get_next_reference()
    return {"reference": reference}


@router.post(
    "/{contract_request_id}/generate-draft",
    response_model=ContractResponse,
    summary="Generate contract draft",
)
async def generate_draft(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF contract draft. ADV/admin only."""
    from app.contract_management.application.use_cases.generate_draft import (
        GenerateDraftUseCase,
    )
    from app.contract_management.infrastructure.adapters.html_pdf_contract_generator import (
        HtmlPdfContractGenerator,
    )
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    article_repo = ArticleTemplateRepository(db)
    annex_repo = AnnexTemplateRepository(db)
    s3_service = S3StorageClient(settings)

    use_case = GenerateDraftUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        contract_generator=HtmlPdfContractGenerator(),
        article_template_repository=article_repo,
        annex_template_repository=annex_repo,
        s3_service=s3_service,
        settings=settings,
        db=db,
    )

    try:
        contract = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("generate_draft_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.DRAFT_GENERATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
    )

    return ContractResponse(
        id=contract.id,
        contract_request_id=contract.contract_request_id,
        reference=contract.reference,
        version=contract.version,
        s3_key_draft=contract.s3_key_draft,
        s3_key_signed=contract.s3_key_signed,
        yousign_status=contract.yousign_status,
        partner_comments=contract.partner_comments,
        created_at=contract.created_at,
        signed_at=contract.signed_at,
    )


@router.post(
    "/{contract_request_id}/send-draft-to-partner",
    response_model=ContractRequestResponse,
    summary="Send draft to partner for review",
)
async def send_draft_to_partner(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Send the contract draft to the partner via magic link. ADV/admin only."""
    from app.contract_management.application.use_cases.send_draft_to_partner import (
        SendDraftToPartnerUseCase,
    )
    from app.infrastructure.email.sender import EmailService
    from app.third_party.application.use_cases.generate_magic_link import (
        GenerateMagicLinkUseCase,
    )
    from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
        MagicLinkRepository,
    )

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)
    ml_repo = MagicLinkRepository(db)
    email_service = EmailService(settings)

    magic_link_uc = GenerateMagicLinkUseCase(
        third_party_repository=tp_repo,
        magic_link_repository=ml_repo,
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
    )

    use_case = SendDraftToPartnerUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        generate_magic_link_use_case=magic_link_uc,
    )

    try:
        cr = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("send_draft_to_partner_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    await _notify_commercial(
        email_service,
        to=cr.commercial_email,
        ref=cr.reference,
        title="Projet de contrat envoyé au partenaire",
        msg=f"Le projet de contrat{client_label} a été transmis au partenaire pour relecture et validation.",
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/send-for-signature",
    response_model=ContractRequestResponse,
    summary="Send contract for electronic signature",
)
async def send_for_signature(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Send the contract to YouSign for signature. ADV/admin only."""
    from app.contract_management.application.use_cases.send_for_signature import (
        SendForSignatureUseCase,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.contract_management.infrastructure.adapters.yousign_client import YouSignClient
    from app.infrastructure.email.sender import EmailService
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    s3_service = S3StorageClient(settings)
    email_service = EmailService(settings)
    yousign = YouSignClient(
        api_key=settings.YOUSIGN_API_KEY,
        base_url=settings.YOUSIGN_API_BASE_URL,
    )

    use_case = SendForSignatureUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        s3_service=s3_service,
        signature_service=yousign,
        settings=settings,
    )

    try:
        cr = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("send_for_signature_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    await _notify_commercial(
        email_service,
        to=cr.commercial_email,
        ref=cr.reference,
        title="Contrat envoyé en signature électronique",
        msg=f"Le contrat{client_label} a été transmis aux signataires via YouSign. Vous serez notifié dès qu'il sera signé.",
        color="#8b5cf6",
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/push-to-crm",
    response_model=ContractRequestResponse,
    summary="Push contract to BoondManager CRM",
)
async def push_to_crm(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Create provider + purchase order in BoondManager. ADV/admin only."""
    from app.contract_management.application.use_cases.push_to_crm import PushToCrmUseCase
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.email.sender import EmailService

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    crm_service = BoondCrmAdapter(BoondClient(settings))
    email_service = EmailService(settings)

    use_case = PushToCrmUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        crm_service=crm_service,
    )

    try:
        cr = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("push_to_crm_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    await _notify_commercial(
        email_service,
        to=cr.commercial_email,
        ref=cr.reference,
        title="Contrat versé dans BoondManager",
        msg=f"Le contrat{client_label} a été archivé et le bon de commande créé dans BoondManager.",
        color="#10b981",
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.get(
    "/{contract_request_id}/contracts",
    response_model=list[ContractResponse],
    summary="List contracts for a request",
)
async def list_contracts(
    contract_request_id: UUID,
    auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """List all contract documents for a request."""
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )

    _user_id, role, email = auth
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)

    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    contract = await contract_repo.get_by_request_id(contract_request_id)
    if not contract:
        return []

    return [
        ContractResponse(
            id=contract.id,
            contract_request_id=contract.contract_request_id,
            reference=contract.reference,
            version=contract.version,
            s3_key_draft=contract.s3_key_draft,
            s3_key_signed=contract.s3_key_signed,
            yousign_status=contract.yousign_status,
            partner_comments=contract.partner_comments,
            created_at=contract.created_at,
            signed_at=contract.signed_at,
        )
    ]


@router.get(
    "/{contract_request_id}/contracts/{contract_id}/download",
    summary="Get presigned download URL for a contract document",
)
async def download_contract(
    contract_request_id: UUID,
    contract_id: UUID,
    auth: ContractAccessUser,
    which: str = "draft",
    db: AsyncSession = Depends(get_db),
):
    """Return a presigned S3 URL to download a contract draft or signed PDF."""
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient

    _user_id, role, email = auth
    settings = get_settings()

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")
    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    contract_repo = ContractRepository(db)
    contract = await contract_repo.get_by_id(contract_id)
    if not contract or contract.contract_request_id != contract_request_id:
        raise HTTPException(status_code=404, detail="Document contractuel non trouvé.")

    s3_key = contract.s3_key_signed if (which == "signed" and contract.s3_key_signed) else contract.s3_key_draft
    s3 = S3StorageClient(settings)
    url = await s3.get_presigned_url(s3_key, expires_in=600)
    return {"url": url}
