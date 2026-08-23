"""Contract management API routes."""

import re
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser, AdvOrAdminUser, ContractAccessUser
from app.config import get_settings
from app.contract_management.api.schemas import (
    ArticleOverridesRequest,
    CommercialValidationRequest,
    ComplianceOverrideRequest,
    ContractConfigRequest,
    ContractRequestListResponse,
    ContractRequestResponse,
    ContractResponse,
    ManualContractRequestCreate,
    SkipDocumentsRequest,
    SupplierDossierCreate,
    SupplierFrameworkSummary,
    SupplierLookupResponse,
)
from app.contract_management.application.use_cases.block_compliance import (
    BlockComplianceUseCase,
)
from app.contract_management.application.use_cases.configure_contract import (
    ConfigureContractUseCase,
)
from app.contract_management.application.use_cases.create_supplier_dossier import (
    CreateSupplierDossierUseCase,
    SupplierDossierCommand,
    siren_from_siret,
)
from app.contract_management.application.use_cases.skip_document_collection import (
    SkipDocumentCollectionUseCase,
)
from app.contract_management.application.use_cases.start_compliance_review import (
    StartComplianceReviewUseCase,
)
from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
    ValidateCommercialUseCase,
)
from app.contract_management.domain.exceptions import (
    ComplianceBlockError,
    ContractRequestNotFoundError,
    InvalidContractStatusError,
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
from app.third_party.api.schemas import CompanyInfoRequest, SiretLookupResponse
from app.third_party.application.company_info_mapper import apply_company_info
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


def _format_siren(siren: str) -> str:
    """Format a SIREN number with spaces every 3 digits (e.g. '894213669' → '894 213 669')."""
    digits = re.sub(r"\D", "", siren)
    return " ".join(digits[i : i + 3] for i in range(0, len(digits), 3))


router = APIRouter(tags=["Contract Management"])


async def _notify_commercial(
    email_service,
    *,
    to: str,
    ref: str,
    title: str,
    msg: str,
    color: str = "#0ea5e9",
    from_email: str | None = None,
    company_name: str | None = None,
) -> None:
    """Fire-and-forget contract progress notification to the commercial."""
    try:
        await email_service.send_contract_progress_to_commercial(
            to=to,
            contract_ref=ref,
            step_title=title,
            step_message=msg,
            step_color=color,
            from_email=from_email,
            company_name=company_name,
        )
    except Exception as exc:
        logger.warning("commercial_notification_failed", error=str(exc), to=to)


async def _resolve_company_email_ctx(db: AsyncSession, company_id) -> tuple[str | None, str | None]:
    """Resolve company email_from and name from company_id.

    Returns (email_from, company_name) for use in email sending.
    """
    if not company_id:
        return None, None
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import ContractCompanyModel

    result = await db.execute(
        select(ContractCompanyModel.email_from, ContractCompanyModel.name).where(
            ContractCompanyModel.id == company_id
        )
    )
    row = result.first()
    if row:
        return row.email_from, row.name
    return None, None


async def _resolve_commercial_name(db: AsyncSession, email: str | None) -> str | None:
    """Resolve a commercial email to full name from users table."""
    if not email:
        return None
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
    third_party_name: str | None = None,
    company_name: str | None = None,
    purchase_orders_count: int = 0,
    portal_url: str | None = None,
) -> ContractRequestResponse:
    """Convert a ContractRequest entity to response."""
    return ContractRequestResponse(
        id=cr.id,
        provisional_reference=cr.provisional_reference,
        reference=cr.reference,
        display_reference=cr.display_reference,
        trigger_type=cr.trigger_type,
        previous_contract_request_id=cr.previous_contract_request_id,
        boond_positioning_id=cr.boond_positioning_id,
        boond_candidate_id=cr.boond_candidate_id,
        boond_consultant_type=cr.boond_consultant_type,
        boond_resource_id=cr.boond_resource_id,
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
        third_party_name=third_party_name,
        portal_url=portal_url,
        compliance_override=cr.compliance_override,
        compliance_override_reason=cr.compliance_override_reason,
        documents_skipped=cr.documents_skipped,
        company_id=cr.company_id,
        company_name=company_name,
        purchase_orders_count=purchase_orders_count,
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

    emails = list({cr.commercial_email for cr in items if cr.commercial_email})
    name_map = await _resolve_commercial_names(db, emails)

    # Resolve third party names for the list
    tp_ids = list({cr.third_party_id for cr in items if cr.third_party_id})
    tp_name_map: dict = {}
    if tp_ids:
        from sqlalchemy import select as _sel

        from app.third_party.infrastructure.models import ThirdPartyModel

        result = await db.execute(
            _sel(ThirdPartyModel.id, ThirdPartyModel.company_name).where(
                ThirdPartyModel.id.in_(tp_ids)
            )
        )
        tp_name_map = {row[0]: row[1] for row in result.all() if row[1]}

    company_name_map = await _issuer_company_names(db, [cr.company_id for cr in items])
    order_counts = await _purchase_order_counts(db, [cr.id for cr in items])

    return ContractRequestListResponse(
        items=[
            _cr_to_response(
                cr,
                commercial_name=name_map.get(cr.commercial_email),
                third_party_name=tp_name_map.get(cr.third_party_id),
                company_name=company_name_map.get(cr.company_id),
                purchase_orders_count=order_counts.get(cr.id, 0),
            )
            for cr in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/manual",
    response_model=ContractRequestResponse,
    summary="Create a contract request manually (ADV/admin, no Boond webhook)",
)
async def create_manual_contract_request(
    body: ManualContractRequestCreate,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a contract request from scratch, entering the Boond resource ID.

    The consultant identity is best-effort enriched from Boond (via the resource
    ID). The request starts in PENDING_COMMERCIAL_VALIDATION and then follows the
    standard flow (commercial validation → third-party info → draft). ADV/admin only.
    """
    from sqlalchemy import select

    from app.contract_management.application.use_cases.create_manual_contract_request import (
        CreateManualContractRequestUseCase,
        ManualContractRequestCommand,
    )
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)

    # Creator email is the commercial fallback when the resource has no manager
    # resolvable to a Bobby user.
    creator_email = ""
    row = (await db.execute(select(UserModel.email).where(UserModel.id == user_id))).first()
    if row and row[0]:
        creator_email = str(row[0])

    crm = BoondCrmAdapter(BoondClient(settings))
    use_case = CreateManualContractRequestUseCase(
        contract_request_repository=cr_repo,
        crm_service=crm,
        user_repository=UserRepository(db),
    )

    try:
        cr = await use_case.execute(
            ManualContractRequestCommand(
                boond_consultant_id=body.boond_consultant_id,
                consultant_type=body.consultant_type,
                commercial_email=creator_email,
                company_id=body.company_id,
                client_name=body.client_name,
                mission_title=body.mission_title,
                consultant_civility=body.consultant_civility,
                consultant_first_name=body.consultant_first_name,
                consultant_last_name=body.consultant_last_name,
                consultant_email=body.consultant_email,
                consultant_phone=body.consultant_phone,
            )
        )
    except Exception as exc:
        logger.error("create_manual_contract_request_failed", error=str(exc))
        raise HTTPException(status_code=400, detail="La création manuelle du contrat a échoué.")

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CREATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(cr.id),
        details={
            "trigger_type": "manual",
            "boond_consultant_id": body.boond_consultant_id,
            "consultant_type": body.consultant_type,
        },
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


# Les routes littérales doivent précéder `/{contract_request_id}` : déclarée
# avant, la route paramétrée capterait « suppliers » et échouerait sur le
# parsing d'UUID.
@router.get(
    "/suppliers/lookup",
    response_model=SupplierLookupResponse,
    summary="Rechercher un fournisseur par SIRET avant d'ouvrir un dossier",
)
async def lookup_supplier(
    siret: str,
    user_id: AdvOrAdminUser,
    company_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Dit si un fournisseur est déjà connu, et où en est sa contractualisation.

    Évite d'ouvrir une seconde fiche pour une société déjà enregistrée — c'est
    ce doublon qui fait redemander au fournisseur des documents de vigilance
    déjà fournis.

    Un contrat cadre lie le fournisseur à **une** société émettrice : avec
    `company_id`, la réponse dit s'il en a un avec celle-ci, et liste dans tous
    les cas ceux qu'il a avec les autres sociétés du groupe. ADV/admin.
    """
    siren = siren_from_siret(siret)
    if not siren:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIRET invalide : au moins 9 chiffres sont attendus.",
        )

    tp_repo = ThirdPartyRepository(db)
    third_party = await tp_repo.get_by_siren(siren)
    if not third_party:
        return SupplierLookupResponse(exists=False, siren=siren)

    cr_repo = ContractRequestRepository(db)
    framework = await cr_repo.get_framework_contract_for_third_party(third_party.id, company_id)
    all_frameworks = await cr_repo.list_framework_contracts_for_third_party(third_party.id)
    issuer_names = await _issuer_company_names(db, [f.company_id for f in all_frameworks])

    # Dossier encore en cours pour ce fournisseur chez la même société : le
    # signaler évite d'en ouvrir un second en parallèle. Un dossier chez une
    # autre société n'a pas à bloquer celui-ci.
    open_cr = next(
        (
            cr
            for cr in await cr_repo.list_by_third_party(third_party.id)
            if cr.status
            not in (
                ContractRequestStatus.SIGNED,
                ContractRequestStatus.ACTIVE,
                ContractRequestStatus.ARCHIVED,
                ContractRequestStatus.CANCELLED,
                ContractRequestStatus.REDIRECTED_PAYFIT,
            )
            and (company_id is None or cr.company_id in (company_id, None))
        ),
        None,
    )

    return SupplierLookupResponse(
        exists=True,
        third_party_id=third_party.id,
        company_name=third_party.company_name,
        siren=third_party.siren or siren,
        compliance_status=third_party.compliance_status.value,
        has_framework_contract=framework is not None,
        framework_contract_id=framework.id if framework else None,
        framework_contract_reference=framework.display_reference if framework else None,
        framework_contracts=[
            SupplierFrameworkSummary(
                contract_request_id=f.id,
                reference=f.display_reference,
                status=f.status.value,
                issuer_company_id=f.company_id,
                issuer_company_name=issuer_names.get(f.company_id),
            )
            for f in all_frameworks
        ],
        open_contract_request_id=open_cr.id if open_cr else None,
        open_contract_request_status=open_cr.status.value if open_cr else None,
    )


async def _purchase_order_counts(db: AsyncSession, contract_request_ids: list) -> dict:
    """Nombre de bons de commande vivants par contrat cadre, en une requête.

    Les bons de commande annulés ne comptent pas : ils ne représentent aucune
    mission.
    """
    from sqlalchemy import func as _func
    from sqlalchemy import select as _sel

    from app.contract_management.infrastructure.models import PurchaseOrderModel

    if not contract_request_ids:
        return {}
    result = await db.execute(
        _sel(PurchaseOrderModel.contract_request_id, _func.count(PurchaseOrderModel.id))
        .where(
            PurchaseOrderModel.contract_request_id.in_(contract_request_ids),
            PurchaseOrderModel.status != "cancelled",
        )
        .group_by(PurchaseOrderModel.contract_request_id)
    )
    return {row[0]: row[1] for row in result.all()}


async def _issuer_company_names(db: AsyncSession, company_ids: list) -> dict:
    """Nom des sociétés émettrices, en une requête."""
    from sqlalchemy import select as _sel

    from app.contract_management.infrastructure.models import ContractCompanyModel

    wanted = [cid for cid in company_ids if cid]
    if not wanted:
        return {}
    result = await db.execute(
        _sel(ContractCompanyModel.id, ContractCompanyModel.name).where(
            ContractCompanyModel.id.in_(wanted)
        )
    )
    return {row[0]: row[1] for row in result.all()}


@router.post(
    "/suppliers",
    response_model=ContractRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir un dossier de contractualisation fournisseur (contrat cadre)",
)
async def create_supplier_dossier(
    body: SupplierDossierCreate,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Ouvre un contrat cadre sans consultant ni positionnement.

    L'ADV saisit le type de tiers, le contact et le mode de collecte : la
    demande part directement en collecte de documents (portail magic link), ou
    en revue de conformité si le dépôt est ignoré. ADV/admin uniquement.
    """
    from sqlalchemy import select as _select

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)
    ml_repo = MagicLinkRepository(db)
    doc_repo = DocumentRepository(db)

    from app.infrastructure.email.sender import EmailService

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
    validate_commercial_uc = ValidateCommercialUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        find_or_create_third_party_use_case=None,
        generate_magic_link_use_case=generate_magic_link_uc,
        request_documents_use_case=request_documents_uc,
        document_repository=doc_repo,
    )

    creator_email = ""
    row = (await db.execute(_select(UserModel.email).where(UserModel.id == user_id))).first()
    if row and row[0]:
        creator_email = str(row[0])

    company_email_from, company_name = await _resolve_company_email_ctx(db, body.company_id)

    use_case = CreateSupplierDossierUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        validate_commercial_use_case=validate_commercial_uc,
    )

    try:
        cr = await use_case.execute(
            SupplierDossierCommand(
                third_party_type=body.third_party_type,
                contact_email=str(body.contact_email),
                company_id=body.company_id,
                siret=body.siret,
                commercial_email=creator_email,
                notify_third_party=body.notify_third_party,
                skip_documents=body.skip_documents,
                reuse_third_party_id=body.reuse_third_party_id,
                from_email=company_email_from,
                company_name=company_name,
            )
        )
    except Exception as exc:
        await db.rollback()
        logger.error("supplier_dossier_creation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La création du dossier fournisseur a échoué.",
        )

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CREATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(cr.id),
        details={
            "source": "supplier_manual",
            "reference": cr.display_reference,
            "notify_third_party": body.notify_third_party,
            "skip_documents": body.skip_documents,
        },
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


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
        # Prioritize link type based on CR status
        if cr.status in (
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
            ContractRequestStatus.PARTNER_APPROVED,
        ):
            purposes = [MagicLinkPurpose.CONTRACT_REVIEW, MagicLinkPurpose.DOCUMENT_UPLOAD]
        else:
            purposes = [MagicLinkPurpose.DOCUMENT_UPLOAD, MagicLinkPurpose.CONTRACT_REVIEW]
        for purpose in purposes:
            active_link = await ml_repo.get_active_by_third_party_and_purpose(
                cr.third_party_id, purpose
            )
            if active_link:
                settings = get_settings()
                portal_url = f"{settings.BOBBY_PORTAL_BASE_URL}/{active_link.token}"
                break

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

    user_id, role, email = access
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
        document_repository=doc_repo,
    )

    # Resolve company email context for emails sent during validation
    cr_for_company = await cr_repo.get_by_id(contract_request_id)
    if not cr_for_company:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")
    if role == "commercial" and cr_for_company.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    company_email_from, company_name = await _resolve_company_email_ctx(
        db, cr_for_company.company_id
    )

    try:
        cmd = ValidateCommercialCommand(
            contract_request_id=contract_request_id,
            third_party_type=body.third_party_type,
            contact_email=body.contact_email,
            company_id=body.company_id,
            consultant_civility=body.consultant_civility,
            consultant_first_name=body.consultant_first_name,
            consultant_last_name=body.consultant_last_name,
            consultant_email=body.consultant_email,
            consultant_phone=body.consultant_phone,
            notify_third_party=body.notify_third_party,
            skip_documents=body.skip_documents,
        )
        cmd.from_email = company_email_from
        cmd.company_name = company_name
        cr = await use_case.execute(cmd)
    except Exception as exc:
        logger.error("validate_commercial_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail="La validation commerciale a échoué.")

    audit_logger.log(
        AuditAction.COMMERCIAL_VALIDATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
    )

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    if cr.documents_skipped:
        await _notify_commercial(
            email_service,
            to=cr.commercial_email,
            ref=cr.display_reference,
            title="Dossier saisi en interne",
            msg=(
                f"Votre validation commerciale a été enregistrée{client_label}. "
                "Le dossier est saisi en interne (ADV) et le dépôt des documents "
                "de vigilance a été ignoré : le fournisseur n'est pas sollicité."
            ),
            from_email=company_email_from,
            company_name=company_name,
        )
    elif cr.status == ContractRequestStatus.COLLECTING_DOCUMENTS:
        if body.notify_third_party:
            collection_msg = (
                f"Votre validation commerciale a été enregistrée{client_label}. "
                "Le tiers a été contacté pour fournir ses documents légaux."
            )
        else:
            collection_msg = (
                f"Votre validation commerciale a été enregistrée{client_label}. "
                "Les informations du tiers seront saisies en interne (ADV), sans "
                "solliciter le fournisseur."
            )
        await _notify_commercial(
            email_service,
            to=cr.commercial_email,
            ref=cr.display_reference,
            title="Collecte de documents lancée",
            msg=collection_msg,
            from_email=company_email_from,
            company_name=company_name,
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


@router.get(
    "/siret-lookup/{siret}",
    response_model=SiretLookupResponse,
    summary="Lookup SIRET via INSEE Sirene API (ADV manual entry)",
)
async def siret_lookup(
    siret: str,
    _user_id: AdvOrAdminUser,
):
    """Auto-fill company identity from a SIRET for ADV manual entry.

    Same INSEE Sirene + INPI RNE source as the portal, but JWT-authenticated so
    the ADV can fill the tiers info without a magic link. ADV/admin only.
    """
    from app.third_party.api.siret_lookup import lookup_siret_data

    return await lookup_siret_data(siret, get_settings())


@router.post(
    "/{contract_request_id}/third-party-info",
    response_model=ContractRequestResponse,
    summary="Enter the third-party company identity + contacts manually (ADV)",
)
async def save_third_party_info(
    contract_request_id: UUID,
    body: CompanyInfoRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Manually enter/update the tiers' company identity and contacts.

    Lets an ADV fill in everything the fournisseur would normally provide via the
    portal — without soliciting it — up to draft generation. Creates the vigilance
    document slots (idempotent) so the ADV can then upload the legal documents (or
    force compliance) before generating the draft. ADV/admin only.
    """
    from app.third_party.domain.entities.third_party import ThirdParty
    from app.third_party.domain.value_objects.third_party_type import ThirdPartyType

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if not cr.third_party_type or cr.third_party_type == "salarie":
        raise HTTPException(
            status_code=400,
            detail=(
                "Effectuez d'abord la validation commerciale (type de tiers) "
                "avant de saisir les informations du tiers."
            ),
        )

    tp_repo = ThirdPartyRepository(db)
    tp = await tp_repo.get_by_id(cr.third_party_id) if cr.third_party_id else None
    if not tp:
        tp = ThirdParty(
            contact_email=cr.contractualization_contact_email or body.representative_email,
            type=ThirdPartyType(cr.third_party_type),
        )
        tp = await tp_repo.save(tp)
        cr.third_party_id = tp.id

    apply_company_info(tp, body)
    await tp_repo.save(tp)

    # Create vigilance document slots based on entity_category (idempotent) so the
    # ADV can upload the legal documents from the contract page. Skipped when the
    # ADV explicitly opted out of the document collection (saisie en personne) —
    # sinon la saisie du tiers recréerait la collecte qu'on vient d'ignorer.
    if not cr.documents_skipped:
        doc_repo = DocumentRepository(db)
        request_documents_uc = RequestDocumentsUseCase(
            third_party_repository=tp_repo,
            document_repository=doc_repo,
        )
        try:
            await request_documents_uc.execute(tp.id, entity_category=body.entity_category)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    saved = await cr_repo.save(cr)
    await db.commit()

    audit_logger.log(
        AuditAction.DOCUMENT_COLLECTION_INITIATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={
            "action": "third_party_info_manual_entry",
            "third_party_id": str(tp.id),
            "siret": body.siret,
        },
    )

    logger.info(
        "third_party_info_manual_entry",
        cr_id=str(saved.id),
        third_party_id=str(tp.id),
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


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

    allowed = {
        CRStatus.COLLECTING_DOCUMENTS,
        CRStatus.REVIEWING_COMPLIANCE,
        CRStatus.COMPLIANCE_BLOCKED,
    }
    if cr.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Le renvoi du lien n'est possible qu'en cours de collecte, vérification ou en conformité bloquée.",
        )

    if cr.documents_skipped:
        raise HTTPException(
            status_code=400,
            detail=(
                "Le dépôt des documents a été ignoré pour cette demande. "
                "Rétablissez la collecte avant de solliciter le tiers."
            ),
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
        company_email_from, company_name = await _resolve_company_email_ctx(db, cr.company_id)
        await generate_magic_link_uc.execute(
            GenerateMagicLinkCommand(
                third_party_id=cr.third_party_id,
                purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
                email=cr.contractualization_contact_email,
                contract_request_id=cr.id,
                from_email=company_email_from,
                company_name=company_name,
            )
        )
    except Exception as exc:
        logger.error("resend_collection_email_failed", error=str(exc))
        raise HTTPException(status_code=400, detail="Le renvoi de l'email de collecte a échoué.")

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
        cr = await use_case.execute(contract_request_id, body.model_dump(mode="json"))
    except Exception as exc:
        logger.error("configure_contract_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail="La configuration du contrat a échoué.")

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
    "/{contract_request_id}/skip-documents",
    response_model=ContractRequestResponse,
    summary="Skip (or restore) the vigilance document collection",
)
async def skip_documents(
    contract_request_id: UUID,
    body: SkipDocumentsRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Ignorer le dépôt des documents de vigilance. ADV/admin uniquement.

    Prévu pour la saisie « en personne » : l'ADV renseigne le dossier lui-même,
    sans passer par le fournisseur, et la vigilance documentaire est traitée hors
    Bobby. La demande est marquée sans collecte, la conformité est levée par
    dérogation tracée et le brouillon devient générable immédiatement.

    `restore=true` fait le chemin inverse : la dérogation est annulée et les
    emplacements de documents sont recréés (si l'identité du tiers est connue).
    """
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)
    doc_repo = DocumentRepository(db)
    request_documents_uc = RequestDocumentsUseCase(
        third_party_repository=tp_repo,
        document_repository=doc_repo,
    )
    use_case = SkipDocumentCollectionUseCase(
        contract_request_repository=cr_repo,
        document_repository=doc_repo,
        third_party_repository=tp_repo,
        request_documents_use_case=request_documents_uc,
    )

    try:
        cr = await use_case.execute(
            contract_request_id,
            reason=body.reason,
            restore=body.restore,
        )
    except ContractRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")
    except InvalidContractStatusError as exc:
        logger.warning(
            "skip_documents_invalid_status",
            error=str(exc),
            cr_id=str(contract_request_id),
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Le statut actuel de la demande ne permet plus de modifier la "
                "collecte des documents de vigilance."
            ),
        )
    except Exception as exc:
        logger.error("skip_documents_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(
            status_code=400,
            detail="La modification de la collecte des documents a échoué.",
        )

    await db.commit()

    audit_logger.log(
        AuditAction.COMPLIANCE_OVERRIDDEN,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={
            "action": "restore_document_collection" if body.restore else "skip_document_collection",
            "reason": body.reason,
        },
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


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
        logger.error(
            "start_compliance_review_failed", error=str(exc), cr_id=str(contract_request_id)
        )
        raise HTTPException(
            status_code=400, detail="Le démarrage de la revue de conformité a échoué."
        )

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
        logger.error("block_compliance_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail="Le blocage de la conformité a échoué.")

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
    """Cancel a contract request (contrat cadre). ADV/admin only.

    Depuis la refonte BDC, un ContractRequest n'est plus lié à un positionnement
    (les contrats cadres proviennent des webhooks candidat/ressource ; les
    positionnements créent des BDC). L'annulation ne dépend donc plus de l'état
    du positionnement Boond — seule la transition de statut du CR est vérifiée.
    """
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

    boond_state = None
    previous_status = cr.status.value
    cr.transition_to(ContractRequestStatus.CANCELLED)
    saved = await cr_repo.save(cr)

    # Remove webhook dedup entries so a new webhook can re-create a CR
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        WebhookEventRepository,
    )

    webhook_repo = WebhookEventRepository(db)
    deleted = 0
    if cr.boond_positioning_id:
        deleted = await webhook_repo.delete_by_prefix(
            f"positioning_update_{cr.boond_positioning_id}_"
        )

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
    _c_email, _c_name = await _resolve_company_email_ctx(db, saved.company_id)
    await _notify_commercial(
        EmailService(settings),
        to=saved.commercial_email,
        ref=saved.reference,
        title="Demande de contrat annulée",
        msg=f"La demande de contrat{client_label} a été annulée (statut précédent : {previous_status}).",
        color="#ef4444",
        from_email=_c_email,
        company_name=_c_name,
    )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


@router.post(
    "/{contract_request_id}/purge",
    summary="Permanently delete a cancelled contract request",
)
async def purge_contract_request(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a cancelled contract request and all related data.

    Only allowed when the contract request is in CANCELLED status.
    ADV/admin only.
    """
    from sqlalchemy import delete as sa_delete

    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        WebhookEventRepository,
    )

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if cr.status != ContractRequestStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Seules les demandes annulées peuvent être supprimées définitivement.",
        )

    # Delete related data (respect FK order)
    from app.contract_management.infrastructure.models import (
        CharterAcknowledgementModel,
        ContractConsultantModel,
        ContractModel,
        ContractRequestModel,
        SignatureUploadModel,
    )
    from app.third_party.infrastructure.models import MagicLinkModel

    # Signature uploads (FK → contract_requests)
    await db.execute(
        sa_delete(SignatureUploadModel).where(
            SignatureUploadModel.contract_request_id == contract_request_id
        )
    )

    # Charter acknowledgements (FK → contract_requests)
    await db.execute(
        sa_delete(CharterAcknowledgementModel).where(
            CharterAcknowledgementModel.contract_request_id == contract_request_id
        )
    )

    # Consultants (FK → contract_requests)
    await db.execute(
        sa_delete(ContractConsultantModel).where(
            ContractConsultantModel.contract_request_id == contract_request_id
        )
    )

    # Generated contracts (FK → contract_requests)
    await db.execute(
        sa_delete(ContractModel).where(ContractModel.contract_request_id == contract_request_id)
    )

    # Magic links (FK → contract_requests)
    await db.execute(
        sa_delete(MagicLinkModel).where(MagicLinkModel.contract_request_id == contract_request_id)
    )

    # Webhook events
    webhook_repo = WebhookEventRepository(db)
    if cr.boond_positioning_id:
        await webhook_repo.delete_by_prefix(f"positioning_update_{cr.boond_positioning_id}_")

    # Delete the contract request itself
    await db.execute(
        sa_delete(ContractRequestModel).where(ContractRequestModel.id == contract_request_id)
    )

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CANCELLED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "purge", "reference": cr.reference},
    )

    return {"status": "ok", "message": f"Demande {cr.display_reference} supprimée définitivement."}


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
    except ComplianceBlockError as exc:
        logger.warning("generate_draft_blocked_by_compliance", error=str(exc))
        raise HTTPException(
            status_code=409,
            detail=(
                "Impossible de générer le brouillon : les documents de vigilance du "
                "sous-traitant ne sont pas encore tous validés. Validez les documents "
                "dans la section « Documents de conformité » (ou forcez la conformité "
                "avec une justification) avant de générer le contrat."
            ),
        )
    except InvalidContractStatusError as exc:
        logger.warning("generate_draft_invalid_status", error=str(exc))
        raise HTTPException(
            status_code=409,
            detail=(
                "Impossible de générer le brouillon : le statut actuel de la demande "
                "ne le permet pas. Vérifiez que la validation commerciale et la revue "
                "de conformité ont bien été effectuées."
            ),
        )
    except Exception as exc:
        logger.error("generate_draft_failed", error=str(exc))
        raise HTTPException(status_code=400, detail="La génération du projet de contrat a échoué.")

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

    # Resolve company email context
    cr_for_ctx = await cr_repo.get_by_id(contract_request_id)
    company_email_from, company_name = await _resolve_company_email_ctx(
        db, cr_for_ctx.company_id if cr_for_ctx else None
    )

    try:
        cr = await use_case.execute(
            contract_request_id, from_email=company_email_from, company_name=company_name
        )
    except Exception as exc:
        logger.error("send_draft_to_partner_failed", error=str(exc))
        raise HTTPException(
            status_code=400, detail="L'envoi du projet de contrat au partenaire a échoué."
        )

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    await _notify_commercial(
        email_service,
        to=cr.commercial_email,
        ref=cr.display_reference,
        title="Projet de contrat envoyé au partenaire",
        msg=f"Le projet de contrat{client_label} a été transmis au partenaire pour relecture et validation.",
        from_email=company_email_from,
        company_name=company_name,
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/approve-draft-internal",
    response_model=ContractRequestResponse,
    summary="Approve the draft internally, on the partner's behalf (ADV/admin)",
)
async def approve_draft_internal(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve the draft without soliciting the partner (fully manual flow).

    Assigns the definitive reference, regenerates the draft with it, and moves to
    PARTNER_APPROVED. The signature that follows is also ADV-side (checklist upload
    + mark-as-signed), so the partner is never contacted. ADV/admin only.
    """
    from app.contract_management.application.use_cases.approve_draft_internally import (
        ApproveDraftInternallyUseCase,
    )
    from app.contract_management.application.use_cases.regenerate_draft import (
        DraftRegenerator,
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

    draft_regenerator = DraftRegenerator(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=ThirdPartyRepository(db),
        contract_generator=HtmlPdfContractGenerator(),
        article_template_repository=ArticleTemplateRepository(db),
        annex_template_repository=AnnexTemplateRepository(db),
        s3_service=S3StorageClient(settings),
        settings=settings,
        db=db,
    )

    use_case = ApproveDraftInternallyUseCase(
        contract_request_repository=cr_repo,
        draft_regenerator=draft_regenerator,
    )

    try:
        cr = await use_case.execute(contract_request_id)
    except ContractRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")
    except InvalidContractStatusError:
        raise HTTPException(
            status_code=409,
            detail=(
                "La validation interne n'est possible que sur un brouillon généré "
                "(ou envoyé au partenaire)."
            ),
        )
    except Exception as exc:
        logger.error(
            "approve_draft_internal_failed", error=str(exc), cr_id=str(contract_request_id)
        )
        raise HTTPException(status_code=400, detail="La validation interne du brouillon a échoué.")

    audit_logger.log(
        AuditAction.DRAFT_GENERATED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_request_id),
        details={"action": "approve_draft_internal"},
    )

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.post(
    "/{contract_request_id}/resend-draft-email",
    response_model=ContractRequestResponse,
    summary="Resend the contract draft review magic link",
)
async def resend_draft_email(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new magic link and resend the draft review email. ADV/admin only."""
    from app.infrastructure.email.sender import EmailService
    from app.third_party.application.use_cases.generate_magic_link import (
        GenerateMagicLinkCommand,
        GenerateMagicLinkUseCase,
    )
    from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
        MagicLinkRepository as MLRepo,
    )
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository as TPRepo,
    )

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if not cr.third_party_id:
        raise HTTPException(status_code=400, detail="Aucun tiers lié à cette demande.")

    contact_email = cr.contractualization_contact_email
    if not contact_email:
        raise HTTPException(status_code=400, detail="Email de contact non renseigné.")

    from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

    email_service = EmailService(settings)
    company_email_from, company_name = await _resolve_company_email_ctx(db, cr.company_id)

    generate_magic_link_uc = GenerateMagicLinkUseCase(
        third_party_repository=TPRepo(db),
        magic_link_repository=MLRepo(db),
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
    )

    try:
        await generate_magic_link_uc.execute(
            GenerateMagicLinkCommand(
                third_party_id=cr.third_party_id,
                purpose=MagicLinkPurpose.CONTRACT_REVIEW,
                email=contact_email,
                contract_request_id=cr.id,
                from_email=company_email_from,
                company_name=company_name,
                contract_ref=cr.display_reference,
            )
        )
    except Exception as exc:
        logger.error("resend_draft_email_failed", error=str(exc))
        raise HTTPException(status_code=400, detail="Le renvoi de l'email de relecture a échoué.")

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.get(
    "/{contract_request_id}/signature-preview",
    summary="Preview documents available for signature",
)
async def get_signature_preview(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Return the list of signable documents for this CR (before sending for signature).

    Each item has: charter_template_id, label, document_kind, signer_role, required (bool).
    The contract itself is always required and not listed here (implicit).
    """
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import CharterTemplateModel

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    if not cr.company_id:
        return []

    result = await db.execute(
        select(CharterTemplateModel)
        .where(
            CharterTemplateModel.company_id == cr.company_id,
            CharterTemplateModel.is_active.is_(True),
        )
        .order_by(CharterTemplateModel.target, CharterTemplateModel.created_at)
    )
    charters = result.scalars().all()

    items = []
    for c in charters:
        needs_signature = c.document_type == "engagement" or c.requires_acknowledgement
        if not needs_signature:
            continue

        # Check consultant scope
        if c.target == "consultant" and c.consultant_scope != "all":
            is_external = cr.third_party_type in ("freelance", "sous_traitant", "portage_salarial")
            if c.consultant_scope == "external" and not is_external:
                continue
            if c.consultant_scope == "internal" and is_external:
                continue

        if c.document_type == "engagement":
            kind = "charter_engagement"
            label = f"{c.name} {c.version}"
        else:
            kind = "charter_ar"
            label = f"AR - {c.name} {c.version}"

        items.append(
            {
                "charter_template_id": str(c.id),
                "label": label,
                "document_kind": kind,
                "signer_role": c.target,
            }
        )

    return items


@router.post(
    "/{contract_request_id}/send-for-signature",
    response_model=ContractRequestResponse,
    summary="Mark contract as sent for signature",
)
async def send_for_signature(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    body: dict | None = None,
):
    """Transition CR to SENT_FOR_SIGNATURE status. ADV/admin only.

    Optionally accepts a list of charter_template_ids to exclude from the signature checklist.
    """
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
        raise HTTPException(status_code=400, detail="Le passage en signature a échoué.")

    # Delete any existing checklist and recreate with exclusions
    from sqlalchemy import delete as sa_delete

    from app.contract_management.infrastructure.models import SignatureUploadModel

    await db.execute(
        sa_delete(SignatureUploadModel).where(
            SignatureUploadModel.contract_request_id == contract_request_id
        )
    )
    excluded_charter_ids = (body or {}).get("excluded_charter_ids", [])
    excluded = set(excluded_charter_ids)
    await _ensure_signature_checklist(db, cr, excluded_charter_ids=excluded)

    name = await _resolve_commercial_name(db, cr.commercial_email)
    return _cr_to_response(cr, commercial_name=name)


@router.get(
    "/{contract_request_id}/signature-checklist",
    summary="Get the list of documents to sign for this contract request",
)
async def get_signature_checklist(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Return the signature checklist (auto-generated from company documents)."""
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import SignatureUploadModel

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    result = await db.execute(
        select(SignatureUploadModel)
        .where(SignatureUploadModel.contract_request_id == contract_request_id)
        .order_by(
            SignatureUploadModel.signer_role,
            SignatureUploadModel.document_kind,
            SignatureUploadModel.created_at,
        )
    )
    rows = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "label": r.label,
            "document_kind": r.document_kind,
            "signer_role": r.signer_role,
            "charter_template_id": str(r.charter_template_id) if r.charter_template_id else None,
            "uploaded": r.s3_key is not None,
            "file_name": r.file_name,
        }
        for r in rows
    ]


@router.post(
    "/{contract_request_id}/signature-checklist/{item_id}/upload",
    summary="Upload a signed document for the signature checklist",
)
async def upload_signature_document(
    contract_request_id: UUID,
    item_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Upload a signed PDF for a specific checklist item. ADV/admin only."""
    from sqlalchemy import select

    from app.config import get_settings
    from app.contract_management.infrastructure.models import SignatureUploadModel
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    result = await db.execute(
        select(SignatureUploadModel).where(
            SignatureUploadModel.id == item_id,
            SignatureUploadModel.contract_request_id == contract_request_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Element introuvable.")

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)

    s3 = S3StorageClient(settings)
    content = await file.read()
    ext = (
        file.filename.rsplit(".", 1)[-1].lower()
        if file.filename and "." in file.filename
        else "pdf"
    )
    ref = cr.display_reference if cr else str(contract_request_id)[:8]
    s3_key = (
        f"contracts/{ref}/signed/{item.document_kind}_{item.signer_role}_{str(item_id)[:8]}.{ext}"
    )

    await s3.upload_file(
        key=s3_key, content=content, content_type=file.content_type or "application/pdf"
    )

    item.s3_key = s3_key
    item.file_name = file.filename
    item.uploaded_at = datetime.utcnow()
    await db.commit()

    return {
        "id": str(item.id),
        "label": item.label,
        "document_kind": item.document_kind,
        "signer_role": item.signer_role,
        "uploaded": True,
        "file_name": item.file_name,
    }


async def _ensure_signature_checklist(db, cr, excluded_charter_ids: set | None = None) -> None:
    """Create signature checklist rows if they don't exist yet (idempotent)."""
    from sqlalchemy import func, select

    from app.contract_management.infrastructure.models import (
        CharterTemplateModel,
        SignatureUploadModel,
    )

    excluded = excluded_charter_ids or set()

    # Check if already created
    count_result = await db.execute(
        select(func.count())
        .select_from(SignatureUploadModel)
        .where(SignatureUploadModel.contract_request_id == cr.id)
    )
    if count_result.scalar() > 0:
        return

    items: list[SignatureUploadModel] = []

    # 1. Always: Contrat cadre signé (partner signs)
    items.append(
        SignatureUploadModel(
            contract_request_id=cr.id,
            document_kind="contract",
            signer_role="partner",
            label="Contrat cadre signe",
        )
    )

    # 2. Company charter documents
    if cr.company_id:
        result = await db.execute(
            select(CharterTemplateModel)
            .where(
                CharterTemplateModel.company_id == cr.company_id,
                CharterTemplateModel.is_active.is_(True),
            )
            .order_by(CharterTemplateModel.target, CharterTemplateModel.created_at)
        )
        charters = result.scalars().all()

        for c in charters:
            # Skip excluded
            if str(c.id) in excluded:
                continue

            needs_signature = c.document_type == "engagement" or c.requires_acknowledgement
            if not needs_signature:
                continue

            signer_role = c.target

            # Check consultant scope
            if c.target == "consultant" and c.consultant_scope != "all":
                is_external = cr.third_party_type in (
                    "freelance",
                    "sous_traitant",
                    "portage_salarial",
                )
                if c.consultant_scope == "external" and not is_external:
                    continue
                if c.consultant_scope == "internal" and is_external:
                    continue

            if c.document_type == "engagement":
                kind = "charter_engagement"
                label = f"{c.name} {c.version}"
            else:
                kind = "charter_ar"
                label = f"AR - {c.name} {c.version}"

            items.append(
                SignatureUploadModel(
                    contract_request_id=cr.id,
                    charter_template_id=c.id,
                    document_kind=kind,
                    signer_role=signer_role,
                    label=label,
                )
            )

    for item in items:
        db.add(item)
    await db.flush()


@router.post(
    "/{contract_request_id}/mark-as-signed",
    response_model=ContractRequestResponse,
    summary="Validate signature (all checklist documents must be uploaded)",
)
async def mark_as_signed(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Check all signature documents are uploaded and transition CR to SIGNED. ADV/admin only."""
    from sqlalchemy import func, select

    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.contract_management.infrastructure.models import SignatureUploadModel

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)

    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    # Ensure checklist exists
    await _ensure_signature_checklist(db, cr)

    # Check all checklist items are uploaded
    total_result = await db.execute(
        select(func.count())
        .select_from(SignatureUploadModel)
        .where(SignatureUploadModel.contract_request_id == contract_request_id)
    )
    total = total_result.scalar() or 0

    uploaded_result = await db.execute(
        select(func.count())
        .select_from(SignatureUploadModel)
        .where(
            SignatureUploadModel.contract_request_id == contract_request_id,
            SignatureUploadModel.s3_key.isnot(None),
        )
    )
    uploaded = uploaded_result.scalar() or 0

    if total == 0 or uploaded < total:
        missing = total - uploaded
        raise HTTPException(
            status_code=400,
            detail=f"Il reste {missing} document(s) a uploader avant de valider la signature.",
        )

    # Get signed contract s3_key from checklist
    contract_item = await db.execute(
        select(SignatureUploadModel).where(
            SignatureUploadModel.contract_request_id == contract_request_id,
            SignatureUploadModel.document_kind == "contract",
        )
    )
    contract_upload = contract_item.scalar_one_or_none()

    contracts = await contract_repo.list_by_contract_request(cr.id)
    if contracts:
        contract = contracts[-1]
        s3_key_signed = contract_upload.s3_key if contract_upload else None
        if s3_key_signed:
            contract.mark_signed(s3_key_signed)
            await contract_repo.save(contract)

    # Transition CR to SIGNED
    try:
        cr.transition_to(ContractRequestStatus.SIGNED)
    except Exception as exc:
        logger.error("mark_as_signed_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail="La validation de la signature a échoué.")

    saved = await cr_repo.save(cr)
    await db.commit()  # Commit SIGNED status before attempting Boond sync

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

    # ── Upload signed documents to Boond (best-effort) ────────────────────
    try:
        await _upload_signed_docs_to_boond(db, saved)
    except Exception as exc:
        logger.error(
            "boond_document_upload_failed",
            cr_id=str(contract_request_id),
            error=str(exc),
        )

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


async def _upload_signed_docs_to_boond(db, cr) -> dict:
    """Upload signed documents to BoondManager entities (best-effort).

    - Contract + partner docs → company (boond_provider_id)
    - Consultant docs → resource (boond_resource_id)
    """
    from sqlalchemy import select

    from app.config import get_settings
    from app.contract_management.infrastructure.models import SignatureUploadModel
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()

    # Resolve Boond IDs
    tp_repo = ThirdPartyRepository(db)
    tp = await tp_repo.get_by_id(cr.third_party_id) if cr.third_party_id else None
    boond_company_id = tp.boond_provider_id if tp else None
    # Re-fetch to get latest Boond IDs (sync may have updated them)
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRequestRepository as _CRRepo,
    )

    cr = await _CRRepo(db).get_by_id(cr.id) or cr
    if cr.third_party_id:
        tp = await tp_repo.get_by_id(cr.third_party_id)
    boond_resource_id = (
        (tp.boond_resource_id if tp else None) or cr.boond_resource_id or cr.boond_candidate_id
    )

    logger.info(
        "boond_doc_upload_ids",
        cr_id=str(cr.id),
        boond_company_id=boond_company_id,
        resolved_resource_id=boond_resource_id,
        tp_boond_resource_id=tp.boond_resource_id if tp else None,
        cr_boond_resource_id=cr.boond_resource_id,
        cr_boond_candidate_id=cr.boond_candidate_id,
    )

    if not boond_company_id and not boond_resource_id:
        logger.info("boond_doc_upload_skipped_no_ids", cr_id=str(cr.id))
        return {"status": "skipped", "message": "Aucun ID Boond disponible (societe ou ressource)."}

    # Get all uploaded signature items
    result = await db.execute(
        select(SignatureUploadModel).where(
            SignatureUploadModel.contract_request_id == cr.id,
            SignatureUploadModel.s3_key.isnot(None),
        )
    )
    items = result.scalars().all()
    if not items:
        return {"status": "skipped", "message": "Aucun document signe a televerse."}

    uploaded = []
    skipped = []
    errors = []
    boond = BoondClient(settings)
    s3 = S3StorageClient(settings)

    for item in items:
        try:
            filename = item.file_name or f"{item.label}.pdf"

            if item.signer_role == "partner" and boond_company_id:
                content = await s3.download_file(item.s3_key)
                await boond.upload_document(
                    parent_type="company",
                    parent_id=boond_company_id,
                    filename=filename,
                    file_content=content,
                )
                uploaded.append(f"{item.label} → societe #{boond_company_id}")
            elif item.signer_role == "consultant" and boond_resource_id:
                content = await s3.download_file(item.s3_key)
                await boond.upload_document(
                    parent_type="resource",
                    parent_id=boond_resource_id,
                    filename=filename,
                    file_content=content,
                    qualify=True,
                )
                uploaded.append(f"{item.label} → ressource #{boond_resource_id}")
            else:
                target = "societe" if item.signer_role == "partner" else "ressource"
                skipped.append(f"{item.label} (pas d'ID Boond {target})")

            logger.info("boond_doc_uploaded", label=item.label, role=item.signer_role)
        except Exception as exc:
            errors.append(f"{item.label}: {exc}")
            logger.warning("boond_doc_upload_item_failed", label=item.label, error=str(exc))

    msg_parts = []
    if uploaded:
        msg_parts.append(f"{len(uploaded)} doc(s) televerse(s)")
    if skipped:
        msg_parts.append(f"{len(skipped)} ignore(s)")
    if errors:
        msg_parts.append(f"{len(errors)} erreur(s)")

    return {
        "status": "ok" if not errors else "partial",
        "message": " · ".join(msg_parts) if msg_parts else "Rien a televerse.",
        "uploaded": uploaded,
        "skipped": skipped,
        "errors": errors,
    }


@router.post(
    "/{contract_request_id}/boond/upload-signed-documents",
    summary="Upload signed documents to BoondManager",
)
async def boond_upload_signed_documents(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Upload all signed checklist documents to BoondManager. ADV/admin only.

    Partner docs → company, consultant docs → resource.
    """
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    result = await _upload_signed_docs_to_boond(db, cr)
    return result


@router.delete(
    "/{contract_request_id}/contracts/{contract_id}",
    summary="Delete a contract document (admin only)",
)
async def delete_contract(
    contract_request_id: UUID,
    contract_id: UUID,
    user_id: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a contract document. Admin only."""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import select as sa_select

    from app.contract_management.infrastructure.models import ContractModel

    result = await db.execute(
        sa_select(ContractModel).where(
            ContractModel.id == contract_id,
            ContractModel.contract_request_id == contract_request_id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat introuvable.")

    ref = contract.reference

    # Delete S3 files (best-effort)
    try:
        from app.config import get_settings
        from app.infrastructure.storage.s3_client import S3StorageClient

        settings = get_settings()
        s3 = S3StorageClient(settings)
        if contract.s3_key_draft:
            await s3.delete_file(contract.s3_key_draft)
        if contract.s3_key_signed:
            await s3.delete_file(contract.s3_key_signed)
    except Exception:
        pass

    await db.execute(sa_delete(ContractModel).where(ContractModel.id == contract_id))

    # Reset CR reference to the previous contract's reference (or None if no more)
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if cr and cr.reference == ref:
        remaining = await db.execute(
            sa_select(ContractModel)
            .where(ContractModel.contract_request_id == contract_request_id)
            .order_by(ContractModel.version.desc())
        )
        last_contract = remaining.scalars().first()
        cr.reference = last_contract.reference if last_contract else None
        await cr_repo.save(cr)

    await db.commit()

    audit_logger.log(
        AuditAction.CONTRACT_REQUEST_CANCELLED,
        AuditResource.CONTRACT_REQUEST,
        user_id=user_id,
        resource_id=str(contract_id),
        details={"action": "delete_contract", "reference": ref},
    )

    return {"status": "ok", "message": f"Contrat {ref} supprime."}


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
        raise HTTPException(
            status_code=400, detail="L'envoi du contrat vers BoondManager a échoué."
        )

    client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
    _c_email, _c_name = await _resolve_company_email_ctx(db, cr.company_id)
    await _notify_commercial(
        email_service,
        to=cr.commercial_email,
        ref=cr.display_reference,
        title="Contrat versé dans BoondManager",
        msg=f"Le contrat{client_label} a été archivé et le bon de commande créé dans BoondManager.",
        color="#10b981",
        from_email=_c_email,
        company_name=_c_name,
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
    if cr.status not in ("signed", "active", "archived"):
        raise HTTPException(
            status_code=400,
            detail="La synchronisation Boond n'est disponible que pour les contrats signes, actifs ou archives.",
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
        raise HTTPException(
            status_code=400, detail="La synchronisation avec BoondManager a échoué."
        )

    logger.info("retry_boond_sync_complete", cr_id=str(saved.id))

    # Commit sync changes (boond_resource_id etc.) before uploading docs
    await db.commit()

    # Also upload signed documents
    try:
        await _upload_signed_docs_to_boond(db, saved)
    except Exception as exc:
        logger.warning("retry_boond_doc_upload_failed", error=str(exc))

    name = await _resolve_commercial_name(db, saved.commercial_email)
    return _cr_to_response(saved, commercial_name=name)


# ── Actions Boond individuelles ────────────────────────────────────────────────


def _boond_deps(db: AsyncSession, settings):
    """Build shared adapters for individual Boond action routes."""
    from app.contract_management.infrastructure.adapters.boond_crm_adapter import BoondCrmAdapter
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.boond.client import BoondClient

    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    crm = BoondCrmAdapter(BoondClient(settings))
    return cr_repo, contract_repo, tp_repo, crm


def _require_signed_or_archived(cr, contract_request_id: UUID):
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")
    if cr.status not in ("signed", "active", "archived"):
        raise HTTPException(
            status_code=400,
            detail="Action disponible uniquement pour les contrats signes, actifs ou archives.",
        )


@router.post(
    "/{contract_request_id}/boond/convert-candidate",
    summary="[Boond] Convertir le candidat en ressource",
)
async def boond_convert_candidate(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Convertit le candidat en ressource (state=3). ADV/admin only."""
    settings = get_settings()
    cr_repo, _cr2, tp_repo, crm = _boond_deps(db, settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    _require_signed_or_archived(cr, contract_request_id)

    if not cr.boond_candidate_id:
        raise HTTPException(status_code=400, detail="Pas de boond_candidate_id sur cette demande.")

    if cr.boond_consultant_type == "resource":
        return {
            "ok": True,
            "boond_candidate_id": cr.boond_candidate_id,
            "converted": False,
            "already_resource": True,
        }

    # Determine state_reason_type_of: 0 = salarié, 1 = externe
    state_reason_type_of = 0 if cr.third_party_type == "salarie" else 1

    # Fetch manager_id from Boond need (required as dependsOn for conversion)
    manager_id: int | None = None
    if cr.boond_need_id:
        try:
            need_data = await crm.get_need(cr.boond_need_id)
            if need_data:
                manager_id = need_data.get("manager_id")
        except Exception:
            pass  # Best-effort: conversion will still be attempted

    try:
        new_resource_id = await crm.convert_candidate_to_resource(
            cr.boond_candidate_id,
            state=3,
            state_reason_type_of=state_reason_type_of,
            type_of=state_reason_type_of,  # 0=salarié, 1=externe
            manager_id=manager_id,
        )
        # Persist the new resource ID and type
        if new_resource_id and new_resource_id != cr.boond_candidate_id:
            cr.boond_candidate_id = new_resource_id
        cr.boond_consultant_type = "resource"
        await cr_repo.save(cr)

        logger.info(
            "boond_convert_candidate_ok",
            cr_id=str(cr.id),
            old_candidate_id=cr.boond_candidate_id,
            new_resource_id=new_resource_id,
        )
        return {
            "ok": True,
            "boond_candidate_id": cr.boond_candidate_id,
            "new_resource_id": new_resource_id,
            "converted": True,
            "already_resource": False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        cause = exc.__cause__ or (getattr(exc, "__context__", None))
        if hasattr(cause, "response"):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        logger.error("boond_convert_candidate_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(
            status_code=400, detail="Erreur lors de la synchronisation avec BoondManager."
        )


@router.post(
    "/{contract_request_id}/boond/create-contract",
    summary="[Boond] Créer le contrat Boond (externe)",
)
async def boond_create_contract(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    resource_id: int | None = None,
):
    """Crée le contrat Boond et lie le fournisseur (externe uniquement). ADV/admin only.

    Args:
        resource_id: Override Boond resource ID (query param). Falls back to cr.boond_candidate_id.
    """
    from sqlalchemy import select as _select

    from app.contract_management.application.use_cases.sync_to_boond_after_signing import (
        _THIRD_PARTY_TYPE_TO_CONTRACT_TYPE,
    )
    from app.contract_management.infrastructure.models import ContractCompanyModel

    settings = get_settings()
    cr_repo, _cr2, tp_repo, crm = _boond_deps(db, settings)

    cr = await cr_repo.get_by_id(contract_request_id)
    _require_signed_or_archived(cr, contract_request_id)

    effective_resource_id = resource_id or cr.boond_candidate_id
    if not effective_resource_id:
        raise HTTPException(
            status_code=400,
            detail="Pas de resource_id fourni et pas de boond_candidate_id sur cette demande.",
        )

    is_external = cr.third_party_type != "salarie"
    if not is_external:
        return {
            "ok": True,
            "contract_created": False,
            "reason": "Type salarié, pas de contrat Boond.",
        }

    if not cr.daily_rate:
        raise HTTPException(status_code=400, detail="TJM manquant sur la demande.")

    # Resolve third party and company
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

    contract_type_of = _THIRD_PARTY_TYPE_TO_CONTRACT_TYPE.get(cr.third_party_type or "", 3)
    start_date_str = None
    if cr.start_date:
        start_date_str = (
            cr.start_date.strftime("%Y-%m-%d")
            if hasattr(cr.start_date, "strftime")
            else str(cr.start_date)
        )
    end_date_str = None
    if cr.end_date:
        end_date_str = (
            cr.end_date.strftime("%Y-%m-%d")
            if hasattr(cr.end_date, "strftime")
            else str(cr.end_date)
        )
    agency_id = company.boond_agency_id if company else None

    try:
        await crm.create_boond_contract(
            resource_id=effective_resource_id,
            positioning_id=cr.boond_positioning_id,
            daily_rate=float(cr.daily_rate),
            type_of=contract_type_of,
            start_date=start_date_str,
            end_date=end_date_str,
            agency_id=agency_id,
        )

        # Link provider if exists
        provider_linked = False
        if tp and tp.boond_provider_id:
            await crm.update_resource_administrative(
                resource_id=effective_resource_id,
                provider_company_id=tp.boond_provider_id,
                provider_contact_id=tp.boond_commercial_contact_id,
            )
            provider_linked = True

        logger.info(
            "boond_create_contract_ok",
            cr_id=str(cr.id),
            candidate_id=cr.boond_candidate_id,
            contract_type_of=contract_type_of,
            provider_linked=provider_linked,
        )
        return {
            "ok": True,
            "contract_created": True,
            "contract_type_of": contract_type_of,
            "provider_linked": provider_linked,
        }
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        cause = exc.__cause__ or (getattr(exc, "__context__", None))
        if hasattr(cause, "response"):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        logger.error("boond_create_contract_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(
            status_code=400, detail="Erreur lors de la synchronisation avec BoondManager."
        )


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
        logger.error(
            "boond_create_company_get_tp_failed", error=str(exc), cr_id=str(contract_request_id)
        )
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du tiers.")
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

        # Build formatted legal fields
        legal_status = None
        if tp.legal_form and tp.capital:
            legal_status = f"{tp.legal_form} au capital de {tp.capital} €"
        registered_office = None
        if tp.rcs_number and tp.rcs_city:
            formatted_siren = _format_siren(tp.rcs_number)
            registered_office = f"{formatted_siren} R.C.S. {tp.rcs_city}"

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
            else:
                # Company exists — update with latest data
                await crm.update_company_information(
                    company_id=provider_id,
                    postcode=tp.head_office_postal_code,
                    address=tp.head_office_street or tp.head_office_address,
                    town=tp.head_office_city,
                    country="France",
                    legal_status=legal_status,
                    registered_office=registered_office,
                )

        if not provider_id:
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
            (
                tp.signatory_civility or tp.representative_civility,
                tp.signatory_first_name or tp.representative_first_name,
                tp.signatory_last_name or tp.representative_last_name,
                tp.signatory_email or tp.representative_email,
                tp.signatory_phone or tp.representative_phone,
                tp.representative_title,
                signatory_types,
                "signataire",
            ),
            (
                tp.adv_contact_civility,
                tp.adv_contact_first_name,
                tp.adv_contact_last_name,
                tp.adv_contact_email,
                tp.adv_contact_phone,
                "ADV",
                [9],
                "adv",
            ),
            (
                tp.billing_contact_civility,
                tp.billing_contact_first_name,
                tp.billing_contact_last_name,
                tp.billing_contact_email,
                tp.billing_contact_phone,
                "Commercial",
                [8],
                "commercial",
            ),
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
                    "civility": civ,
                    "first_name": fn,
                    "last_name": ln,
                    "email": email,
                    "phone": phone,
                    "job_title": job_title,
                    "types_of": list(types_of_list),
                    "labels": [label],
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
            contacts_created.append(
                {
                    "label": " + ".join(entry["labels"]),
                    "boond_contact_id": contact_id,
                }
            )
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
        cause = exc.__cause__ or (getattr(exc, "__context__", None))
        if hasattr(cause, "response"):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        elif hasattr(exc, "last_attempt"):
            inner = exc.last_attempt.exception()
            if inner and hasattr(inner, "response"):
                detail = f"Boond HTTP {inner.response.status_code}: {inner.response.text[:2000]}"
            elif inner:
                detail = str(inner)
        logger.error("boond_create_company_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(
            status_code=400, detail="Erreur lors de la synchronisation avec BoondManager."
        )


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
        cause = exc.__cause__ or (getattr(exc, "__context__", None))
        if hasattr(cause, "response"):
            detail = f"Boond HTTP {cause.response.status_code}: {cause.response.text[:2000]}"
        elif hasattr(exc, "last_attempt"):
            inner = exc.last_attempt.exception()
            if inner and hasattr(inner, "response"):
                detail = f"Boond HTTP {inner.response.status_code}: {inner.response.text[:2000]}"
            elif inner:
                detail = str(inner)
        logger.error("boond_create_po_failed", error=detail, cr_id=str(contract_request_id))
        raise HTTPException(
            status_code=400, detail="Erreur lors de la synchronisation avec BoondManager."
        )


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

    s3_key = (
        contract.s3_key_signed
        if (which == "signed" and contract.s3_key_signed)
        else contract.s3_key_draft
    )
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

    Admin/ADV only — intended for testing purposes. Disabled in production.
    """
    if get_settings().is_production:
        raise HTTPException(status_code=404, detail="Not found")

    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    try:
        cr.rollback_to_previous_status()
    except Exception as exc:
        logger.error("rollback_status_failed", error=str(exc), cr_id=str(contract_request_id))
        raise HTTPException(status_code=400, detail="Le retour au statut précédent a échoué.")

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


# ── Contract Consultants ─────────────────────────────────────────────────────


@router.get(
    "/{contract_request_id}/consultants",
    summary="List consultants for a contract",
)
async def list_consultants(
    contract_request_id: UUID,
    auth: ContractAccessUser,
    db: AsyncSession = Depends(get_db),
):
    """List consultants linked to a contract for charter tracking."""
    from sqlalchemy import select

    from app.contract_management.infrastructure.models import ContractConsultantModel

    _user_id, role, email = auth
    cr = await ContractRequestRepository(db).get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")
    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    result = await db.execute(
        select(ContractConsultantModel)
        .where(ContractConsultantModel.contract_request_id == contract_request_id)
        .order_by(ContractConsultantModel.created_at)
    )
    consultants = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "phone": c.phone,
            "charter_status": c.charter_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in consultants
    ]


@router.post(
    "/{contract_request_id}/consultants",
    summary="Add a consultant to a contract",
)
async def add_consultant(
    contract_request_id: UUID,
    body: dict,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Add a consultant to a contract for charter tracking. ADV/admin only."""
    from app.contract_management.infrastructure.models import ContractConsultantModel

    cr = await ContractRequestRepository(db).get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat introuvable.")

    consultant = ContractConsultantModel(
        contract_request_id=contract_request_id,
        first_name=body.get("first_name", ""),
        last_name=body.get("last_name", ""),
        email=body.get("email", ""),
        phone=body.get("phone"),
        boond_candidate_id=body.get("boond_candidate_id"),
        charter_status="pending",
    )
    db.add(consultant)
    await db.commit()
    await db.refresh(consultant)

    return {
        "id": str(consultant.id),
        "first_name": consultant.first_name,
        "last_name": consultant.last_name,
        "email": consultant.email,
        "phone": consultant.phone,
        "charter_status": consultant.charter_status,
    }


@router.delete(
    "/{contract_request_id}/consultants/{consultant_id}",
    summary="Remove a consultant from a contract",
)
async def remove_consultant(
    contract_request_id: UUID,
    consultant_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove a consultant from a contract. ADV/admin only."""
    from sqlalchemy import delete

    from app.contract_management.infrastructure.models import ContractConsultantModel

    await db.execute(
        delete(ContractConsultantModel).where(
            ContractConsultantModel.id == consultant_id,
            ContractConsultantModel.contract_request_id == contract_request_id,
        )
    )
    await db.commit()


@router.post(
    "/{contract_request_id}/consultants/{consultant_id}/send-charters",
    summary="Generate and send charter documents for a consultant",
)
async def send_consultant_charters(
    contract_request_id: UUID,
    consultant_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate AR + engagement PDFs and upload to S3. ADV/admin only.

    Updates consultant charter_status to 'sent'.
    """
    from sqlalchemy import select

    from app.contract_management.application.use_cases.generate_charter_documents import (
        GenerateCharterDocumentsUseCase,
    )
    from app.contract_management.infrastructure.models import ContractConsultantModel
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)

    result = await db.execute(
        select(ContractConsultantModel).where(
            ContractConsultantModel.id == consultant_id,
            ContractConsultantModel.contract_request_id == contract_request_id,
        )
    )
    consultant = result.scalar_one_or_none()
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant introuvable.")

    s3 = S3StorageClient(settings)

    use_case = GenerateCharterDocumentsUseCase(
        contract_request_repository=cr_repo,
        s3_service=s3,
        db=db,
    )

    try:
        result_keys = await use_case.execute(
            contract_request_id=contract_request_id,
            consultant_first_name=consultant.first_name,
            consultant_last_name=consultant.last_name,
            consultant_email=consultant.email,
            consultant_phone=consultant.phone or "",
        )
    except Exception as exc:
        logger.error(
            "send_consultant_charters_failed",
            error=str(exc),
            cr_id=str(contract_request_id),
        )
        raise HTTPException(status_code=400, detail="L'envoi des chartes au consultant a échoué.")

    consultant.charter_status = "sent"
    await db.commit()

    return {
        "status": "ok",
        "consultant_id": str(consultant.id),
        "charter_status": "sent",
        "documents": result_keys,
    }


@router.post(
    "/{contract_request_id}/generate-partner-charters",
    summary="Generate the partner charter documents for a contract request",
)
async def generate_partner_charters(
    contract_request_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate the charte des achats responsables and its AR. ADV/admin only.

    Companion of `send-charters`, which covers the consultant documents.
    """
    from app.contract_management.application.use_cases.generate_charter_documents import (
        GenerateCharterDocumentsUseCase,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()

    use_case = GenerateCharterDocumentsUseCase(
        contract_request_repository=ContractRequestRepository(db),
        s3_service=S3StorageClient(settings),
        db=db,
        third_party_repository=ThirdPartyRepository(db),
    )

    try:
        result_keys = await use_case.execute(
            contract_request_id=contract_request_id,
            target="partner",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "generate_partner_charters_failed",
            error=str(exc),
            cr_id=str(contract_request_id),
        )
        raise HTTPException(
            status_code=400, detail="La génération des chartes partenaire a échoué."
        ) from exc

    return {"status": "ok", "documents": result_keys}
