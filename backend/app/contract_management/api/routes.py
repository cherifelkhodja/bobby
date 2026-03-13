"""Contract management API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
        provisional_reference=cr.provisional_reference,
        reference=cr.reference,
        display_reference=cr.display_reference,
        boond_positioning_id=cr.boond_positioning_id,
        boond_candidate_id=cr.boond_candidate_id,
        boond_consultant_type=cr.boond_consultant_type,
        status=cr.status.value,
        status_display=cr.status.display_name,
        third_party_type=cr.third_party_type,
        daily_rate=float(cr.daily_rate) if cr.daily_rate else None,
        quantity_sold=cr.quantity_sold,
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
        company_id=cr.company_id,
        contract_config=cr.contract_config,
        status_history=cr.status_history or [],
        created_at=cr.created_at,
        updated_at=cr.updated_at,
    )


@router.get(
    "/companies",
    summary="List contract companies (active)",
)
async def list_companies(
    _auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """List active contract companies. Accessible to commercial/adv/admin."""
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import ContractCompanyModel

    result = await db.execute(
        select(ContractCompanyModel).where(ContractCompanyModel.is_active.is_(True))
    )
    companies = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "code": c.code,
            "is_active": c.is_active,
            "is_default": c.is_default,
            "invoices_company_mail": c.invoices_company_mail,
        }
        for c in companies
    ]


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

    raw_quantity = positioning_data.get("quantity")
    if raw_quantity is not None:
        try:
            cr.quantity_sold = int(raw_quantity)
        except (ValueError, TypeError):
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

            # Resolve société émettrice from the need's agency (only if not already set)
            agency_id = need_data.get("agency_id")
            if agency_id and not cr.company_id:
                resolved = await cr_repo.get_company_by_boond_agency_id(agency_id)
                if resolved:
                    cr.company_id = resolved
                    logger.info(
                        "company_resolved_from_agency_sync",
                        agency_id=agency_id,
                        company_id=str(resolved),
                        cr_id=str(cr.id),
                    )

    # Sync consultant info from positioning candidate
    candidate_id = positioning_data.get("candidate_id")
    if candidate_id:
        candidate_info = await crm.get_candidate_info(candidate_id)
        if candidate_info:
            cr.consultant_civility = candidate_info.get("civility") or None
            cr.consultant_first_name = candidate_info.get("first_name") or None
            cr.consultant_last_name = candidate_info.get("last_name") or None
            cr.consultant_email = candidate_info.get("email") or None
            cr.consultant_phone = candidate_info.get("phone") or None

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
                quantity_sold=body.quantity_sold,
                start_date=body.start_date,
                end_date=body.end_date,
                contact_email=body.contact_email,
                client_name=body.client_name,
                mission_title=body.mission_title,
                mission_description=body.mission_description,
                company_id=body.company_id,
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
            ref=cr.display_reference,
            title="Collecte de documents lancée",
            msg=f"Votre validation commerciale a été enregistrée{client_label}. Le tiers a été contacté pour fournir ses documents légaux.",
        )
    elif cr.status == ContractRequestStatus.REDIRECTED_PAYFIT:
        await _notify_commercial(
            email_service,
            to=cr.commercial_email,
            ref=cr.display_reference,
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

    # Custom articles/annexes — None means "no change"
    if body.custom_articles is not None:
        cfg["custom_articles"] = [a.model_dump() for a in body.custom_articles]
    if body.custom_annexes is not None:
        cfg["custom_annexes"] = [a.model_dump() for a in body.custom_annexes]

    # Ordering — None means "no change", [] means "reset to default"
    if body.article_order is not None:
        cfg["article_order"] = body.article_order if body.article_order else []
    if body.annex_order is not None:
        cfg["annex_order"] = body.annex_order if body.annex_order else []

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
        ref=cr.display_reference,
        title="Projet de contrat envoyé au partenaire",
        msg=f"Le projet de contrat{client_label} a été transmis au partenaire pour relecture et validation.",
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/send-for-signature",
    response_model=ContractRequestResponse,
    summary="Mark contract as sent for signature",
)
async def send_for_signature(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Transition CR to SENT_FOR_SIGNATURE status. ADV/admin only."""
    from app.contract_management.application.use_cases.send_for_signature import (
        SendForSignatureUseCase,
    )

    cr_repo = ContractRequestRepository(db)

    use_case = SendForSignatureUseCase(
        contract_request_repository=cr_repo,
    )

    try:
        cr = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("send_for_signature_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/mark-as-signed",
    response_model=ContractRequestResponse,
    summary="Mark contract as signed and upload signed document",
)
async def mark_as_signed(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Upload the signed contract document and transition CR to SIGNED. ADV/admin only."""
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    s3_service = S3StorageClient(settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    contracts = await contract_repo.list_by_contract_request(cr.id)
    if not contracts:
        raise HTTPException(status_code=400, detail="Aucun contrat généré pour cette demande.")

    contract = contracts[-1]

    # Upload signed document to S3
    content = await file.read()
    extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "pdf"
    s3_key_signed = f"contracts/{contract.reference}/signed_v{contract.version}.{extension}"
    await s3_service.upload_file(
        key=s3_key_signed,
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )

    # Mark contract as signed
    contract.mark_signed(s3_key_signed)
    await contract_repo.save(contract)

    # Transition CR to SIGNED
    try:
        cr.transition_to(ContractRequestStatus.SIGNED)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    saved = await cr_repo.save(cr)

    logger.info(
        "contract_marked_as_signed",
        cr_id=str(saved.id),
        contract_id=str(contract.id),
        s3_key=s3_key_signed,
    )

    # ── Synchronisation BoondManager (best-effort) ────────────────────────
    try:
        from app.contract_management.application.use_cases.sync_to_boond_after_signing import (
            SyncToBoondAfterSigningUseCase,
        )
        from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
            BoondCrmAdapter,
        )
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            ContractRepository as _ContractRepo,
        )
        from app.infrastructure.boond.client import BoondClient

        _settings = get_settings()
        _cr_repo2 = ContractRequestRepository(db)
        _contract_repo2 = _ContractRepo(db)
        _tp_repo = ThirdPartyRepository(db)
        _crm = BoondCrmAdapter(BoondClient(_settings))

        sync_use_case = SyncToBoondAfterSigningUseCase(
            db=db,
            contract_request_repository=_cr_repo2,
            contract_repository=_contract_repo2,
            third_party_repository=_tp_repo,
            crm_service=_crm,
        )
        saved = await sync_use_case.execute(contract_request_id)
        logger.info("boond_sync_after_signing_complete", cr_id=str(saved.id))
    except Exception as exc:
        logger.error(
            "boond_sync_after_signing_failed",
            cr_id=str(contract_request_id),
            error=str(exc),
        )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


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
        ref=cr.display_reference,
        title="Contrat versé dans BoondManager",
        msg=f"Le contrat{client_label} a été archivé et le bon de commande créé dans BoondManager.",
        color="#10b981",
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/retry-boond-sync",
    response_model=ContractRequestResponse,
    summary="Retry Boond synchronisation after signing",
)
async def retry_boond_sync(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Re-run all Boond sync operations (company, contacts, contract, purchase order).

    Usable when status is SIGNED or ARCHIVED.
    ADV/admin only.
    """
    from app.contract_management.application.use_cases.sync_to_boond_after_signing import (
        SyncToBoondAfterSigningUseCase,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.boond.client import BoondClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    crm_service = BoondCrmAdapter(BoondClient(settings))

    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")
    if cr.status not in ("signed", "archived"):
        raise HTTPException(
            status_code=400,
            detail="La synchronisation Boond n'est disponible que pour les contrats signés ou archivés.",
        )

    use_case = SyncToBoondAfterSigningUseCase(
        db=db,
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        crm_service=crm_service,
    )

    try:
        saved = await use_case.execute(contract_request_id)
    except Exception as exc:
        logger.error("retry_boond_sync_failed", cr_id=str(contract_request_id), error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("retry_boond_sync_complete", cr_id=str(saved.id))
    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


# ── Actions Boond individuelles ────────────────────────────────────────────────

def _boond_deps(db: AsyncSession, settings):
    """Build shared adapters for individual Boond action routes."""
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import BoondCrmAdapter
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import ContractRepository
    from app.infrastructure.boond.client import BoondClient

    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    crm = BoondCrmAdapter(BoondClient(settings))
    return cr_repo, contract_repo, tp_repo, crm


def _require_signed_or_archived(cr, contract_request_id: UUID):
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")
    if cr.status not in ("signed", "archived"):
        raise HTTPException(
            status_code=400,
            detail="Action disponible uniquement pour les contrats signés ou archivés.",
        )


@router.post(
    "/{contract_request_id}/boond/convert-candidate",
    summary="[Boond] Convertir le candidat en ressource + créer contrat Boond",
)
async def boond_convert_candidate(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Convertit le candidat en ressource (state=3) puis crée le contrat Boond (externe). ADV/admin only."""
    from app.contract_management.application.use_cases.sync_to_boond_after_signing import (
        _THIRD_PARTY_TYPE_TO_CONTRACT_TYPE,
    )
    from app.contract_management.infrastructure.models import ContractCompanyModel
    from sqlalchemy import select as _select

    settings = get_settings()
    cr_repo, _cr2, tp_repo, crm = _boond_deps(db, settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    _require_signed_or_archived(cr, contract_request_id)

    if not cr.boond_candidate_id:
        raise HTTPException(status_code=400, detail="Pas de boond_candidate_id sur cette demande.")

    # Resolve third party and company for extra context
    tp = None
    if cr.third_party_id:
        tp = await tp_repo.get_by_id(cr.third_party_id)

    company = None
    if cr.company_id:
        result = await db.execute(
            _select(ContractCompanyModel).where(ContractCompanyModel.id == cr.company_id)
        )
        company = result.scalar_one_or_none()
    if not company:
        result = await db.execute(
            _select(ContractCompanyModel)
            .where(ContractCompanyModel.is_default.is_(True))
            .where(ContractCompanyModel.is_active.is_(True))
            .limit(1)
        )
        company = result.scalar_one_or_none()

    # Determine state_reason_type_of: 0 = salarié, 1 = externe
    state_reason_type_of = 0 if cr.third_party_type == "salarie" else 1

    try:
        # Step 1: Convert candidate → resource (skip if already a resource)
        converted = False
        if cr.boond_consultant_type != "resource":
            await crm.convert_candidate_to_resource(
                cr.boond_candidate_id,
                state=3,
                state_reason_type_of=state_reason_type_of,
            )
            converted = True
            logger.info("boond_convert_candidate_ok", cr_id=str(cr.id), candidate_id=cr.boond_candidate_id)

        # Step 2: Create Boond contract (external resources only)
        contract_created = False
        provider_linked = False
        contract_type_of = None
        resource_type_of = await crm.get_resource_type_of(cr.boond_candidate_id)
        if resource_type_of == 1:  # externe
            if not cr.daily_rate:
                raise HTTPException(status_code=400, detail="TJM manquant sur la demande.")
            contract_type_of = _THIRD_PARTY_TYPE_TO_CONTRACT_TYPE.get(cr.third_party_type or "", 3)

            # Extract start_date from contract request
            start_date_str = None
            if cr.start_date:
                start_date_str = cr.start_date.strftime("%Y-%m-%d") if hasattr(cr.start_date, "strftime") else str(cr.start_date)

            agency_id = company.boond_agency_id if company else None

            await crm.create_boond_contract(
                resource_id=cr.boond_candidate_id,
                positioning_id=cr.boond_positioning_id,
                daily_rate=float(cr.daily_rate),
                type_of=contract_type_of,
                start_date=start_date_str,
                agency_id=agency_id,
            )
            contract_created = True

            # Link provider if exists, using persisted commercial contact ID
            if tp and tp.boond_provider_id:
                await crm.update_resource_administrative(
                    resource_id=cr.boond_candidate_id,
                    provider_company_id=tp.boond_provider_id,
                    provider_contact_id=tp.boond_commercial_contact_id,
                )
                provider_linked = True

        logger.info(
            "boond_convert_and_contract_ok",
            cr_id=str(cr.id),
            candidate_id=cr.boond_candidate_id,
            converted=converted,
            contract_created=contract_created,
        )
        return {
            "ok": True,
            "boond_candidate_id": cr.boond_candidate_id,
            "converted": converted,
            "contract_created": contract_created,
            "contract_type_of": contract_type_of,
            "provider_linked": provider_linked,
        }
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        cause = exc.__cause__ or (getattr(exc, '__context__', None))
        if hasattr(cause, 'response'):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        elif hasattr(exc, 'last_attempt'):
            inner = exc.last_attempt.exception()
            if inner and hasattr(inner, 'response'):
                detail = f"Boond HTTP {inner.response.status_code}: {inner.response.text[:2000]}"
            elif inner:
                detail = str(inner)
        logger.error("boond_convert_candidate_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail=f"Erreur Boond: {detail}")


@router.post(
    "/{contract_request_id}/boond/create-company",
    summary="[Boond] Créer la société fournisseur + contacts",
)
async def boond_create_company(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Crée la société et les 3 contacts (dirigeant, ADV, facturation) dans Boond. ADV/admin only."""
    from app.contract_management.infrastructure.models import ContractCompanyModel
    settings = get_settings()
    cr_repo, _cr2, tp_repo, crm = _boond_deps(db, settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    _require_signed_or_archived(cr, contract_request_id)

    if not cr.third_party_id:
        raise HTTPException(status_code=400, detail="Pas de tiers associé à cette demande.")

    try:
        tp = await tp_repo.get_by_id(cr.third_party_id)
    except Exception as exc:
        logger.error("boond_create_company_get_tp_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=500, detail=f"Erreur chargement tiers: {exc}")
    if not tp:
        raise HTTPException(status_code=404, detail="Tiers introuvable.")

    # Fetch issuing company for agency_id
    from sqlalchemy import select as _select
    company = None
    if cr.company_id:
        result = await db.execute(
            _select(ContractCompanyModel).where(ContractCompanyModel.id == cr.company_id)
        )
        company = result.scalar_one_or_none()
    if not company:
        result = await db.execute(
            _select(ContractCompanyModel)
            .where(ContractCompanyModel.is_default.is_(True))
            .where(ContractCompanyModel.is_active.is_(True))
            .limit(1)
        )
        company = result.scalar_one_or_none()

    try:
        provider_id = tp.boond_provider_id
        created_company = False

        # Verify the cached provider_id still exists in Boond (may have been deleted)
        if provider_id:
            exists = await crm.verify_company_exists(provider_id)
            if not exists:
                logger.warning(
                    "boond_provider_id_stale",
                    cr_id=str(cr.id),
                    stale_id=provider_id,
                )
                provider_id = None
                tp.boond_provider_id = None

        if not provider_id:
            legal_status = None
            if tp.legal_form and tp.capital:
                legal_status = f"{tp.legal_form} au capital de {tp.capital}"
            registered_office = None
            if tp.rcs_number and tp.rcs_city:
                registered_office = f"{tp.rcs_number} R.C.S. {tp.rcs_city}"

            provider_id = await crm.create_company_full(
                company_name=tp.company_name or "",
                state=9,
                postcode=tp.head_office_postal_code,
                address=tp.head_office_street or tp.head_office_address,
                town=tp.head_office_city,
                country="France",
                vat_number=tp.vat_number,
                siret=tp.siret,
                legal_status=legal_status,
                registered_office=registered_office,
                ape_code=tp.ape_code or "6202A",
                agency_id=company.boond_agency_id if company else None,
            )
            tp.boond_provider_id = provider_id
            await tp_repo.save(tp)
            created_company = True
            logger.info("boond_create_company_ok", cr_id=str(cr.id), provider_id=provider_id)

        # Build deduplicated contacts
        # Boond typesOf: 7=dirigeant, 8=commercial, 9=adv, 10=signataire
        signatory_types = [10]  # signataire
        if tp.signatory_is_director:
            signatory_types.append(7)  # dirigeant

        role_entries: list[tuple] = [
            (tp.signatory_civility or tp.representative_civility,
             tp.signatory_first_name or tp.representative_first_name,
             tp.signatory_last_name or tp.representative_last_name,
             tp.signatory_email or tp.representative_email,
             tp.signatory_phone or tp.representative_phone,
             tp.representative_title, signatory_types, "signataire"),
            (tp.adv_contact_civility, tp.adv_contact_first_name, tp.adv_contact_last_name,
             tp.adv_contact_email, tp.adv_contact_phone, "ADV", [9], "adv"),
            (tp.billing_contact_civility, tp.billing_contact_first_name, tp.billing_contact_last_name,
             tp.billing_contact_email, tp.billing_contact_phone, "Commercial", [8], "commercial"),
        ]

        # Group by identity key (normalized first_name + last_name + email)
        merged: dict[str, dict] = {}
        for civ, fn, ln, email, phone, job_title, types_of_list, label in role_entries:
            if not (fn or email):
                continue
            key = f"{(fn or '').strip().lower()}|{(ln or '').strip().lower()}|{(email or '').strip().lower()}"
            if key in merged:
                merged[key]["types_of"].extend(types_of_list)
                merged[key]["labels"].append(label)
                if job_title and job_title not in ("ADV", "Commercial"):
                    merged[key]["job_title"] = job_title
            else:
                merged[key] = {
                    "civility": civ, "first_name": fn, "last_name": ln,
                    "email": email, "phone": phone, "job_title": job_title,
                    "types_of": list(types_of_list), "labels": [label],
                }

        agency_id = company.boond_agency_id if company else None
        postcode = tp.head_office_postal_code

        contacts_created = []
        label_to_contact_id: dict[str, int] = {}
        for entry in merged.values():
            contact_id = await crm.create_contact(
                company_id=provider_id,
                civility=entry["civility"],
                first_name=entry["first_name"],
                last_name=entry["last_name"],
                email=entry["email"],
                phone=entry["phone"],
                job_title=entry["job_title"],
                types_of=entry["types_of"],
                postcode=postcode,
                address=tp.head_office_street or tp.head_office_address,
                town=tp.head_office_city,
                agency_id=agency_id,
            )
            contacts_created.append({
                "label": " + ".join(entry["labels"]),
                "boond_contact_id": contact_id,
            })
            for lbl in entry["labels"]:
                label_to_contact_id[lbl] = contact_id

        # Persist Boond contact IDs on the ThirdParty for future reference
        if label_to_contact_id.get("signataire"):
            tp.boond_signatory_contact_id = label_to_contact_id["signataire"]
        if label_to_contact_id.get("adv"):
            tp.boond_adv_contact_id = label_to_contact_id["adv"]
        if label_to_contact_id.get("commercial"):
            tp.boond_commercial_contact_id = label_to_contact_id["commercial"]
        if label_to_contact_id:
            await tp_repo.save(tp)

        return {
            "ok": True,
            "created_company": created_company,
            "boond_provider_id": provider_id,
            "contacts_created": contacts_created,
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Extract the real Boond error from RetryError / HTTPStatusError chain
        detail = str(exc)
        cause = exc.__cause__ or (getattr(exc, '__context__', None))
        if hasattr(cause, 'response'):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        elif hasattr(exc, 'last_attempt'):
            inner = exc.last_attempt.exception()
            if inner and hasattr(inner, 'response'):
                detail = f"Boond HTTP {inner.response.status_code}: {inner.response.text[:2000]}"
            elif inner:
                detail = str(inner)
        logger.error("boond_create_company_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail=f"Erreur Boond: {detail}")


@router.post(
    "/{contract_request_id}/boond/create-purchase-order",
    summary="[Boond] Créer le bon de commande",
)
async def boond_create_purchase_order(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Crée le bon de commande dans Boond et enregistre l'ID sur le contrat. ADV/admin only."""
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import ContractRepository
    settings = get_settings()
    cr_repo, contract_repo, tp_repo, crm = _boond_deps(db, settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    _require_signed_or_archived(cr, contract_request_id)

    if not cr.daily_rate:
        raise HTTPException(status_code=400, detail="TJM manquant sur la demande.")
    if not cr.third_party_id:
        raise HTTPException(status_code=400, detail="Pas de tiers associé.")

    tp = await tp_repo.get_by_id(cr.third_party_id)
    if not tp or not tp.boond_provider_id:
        raise HTTPException(
            status_code=400,
            detail="La société fournisseur n'a pas encore été créée dans Boond (boond_provider_id manquant).",
        )

    contract = await contract_repo.get_by_request_id(cr.id)
    if not contract:
        raise HTTPException(status_code=400, detail="Aucun contrat signé trouvé.")

    try:
        po_id = await crm.create_purchase_order(
            provider_id=tp.boond_provider_id,
            positioning_id=cr.boond_positioning_id,
            reference=cr.display_reference,
            amount=float(cr.daily_rate),
        )
        contract.boond_purchase_order_id = po_id
        await contract_repo.save(contract)

        logger.info("boond_create_po_ok", cr_id=str(cr.id), po_id=po_id)
        return {"ok": True, "boond_purchase_order_id": po_id}
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        cause = exc.__cause__ or (getattr(exc, '__context__', None))
        if hasattr(cause, 'response'):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        elif hasattr(exc, 'last_attempt'):
            inner = exc.last_attempt.exception()
            if inner and hasattr(inner, 'response'):
                detail = f"Boond HTTP {inner.response.status_code}: {inner.response.text[:2000]}"
            elif inner:
                detail = str(inner)
        logger.error("boond_create_po_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail=f"Erreur Boond: {detail}")


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

    contracts = await contract_repo.list_by_contract_request(contract_request_id)
    return [
        ContractResponse(
            id=c.id,
            contract_request_id=c.contract_request_id,
            reference=c.reference,
            version=c.version,
            s3_key_draft=c.s3_key_draft,
            s3_key_signed=c.s3_key_signed,
            yousign_status=c.yousign_status,
            partner_comments=c.partner_comments,
            created_at=c.created_at,
            signed_at=c.signed_at,
        )
        for c in contracts
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


@router.post(
    "/{contract_request_id}/rollback",
    response_model=ContractRequestResponse,
    summary="Rollback to previous status (admin only, testing)",
)
async def rollback_status(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Rollback a contract request to its previous status.

    Admin/ADV only — intended for testing purposes.
    """
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    try:
        cr.rollback_to_previous_status()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    saved = await cr_repo.save(cr)

    audit_logger.log(
        AuditAction.COMMERCIAL_VALIDATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "rollback", "new_status": saved.status.value},
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)
