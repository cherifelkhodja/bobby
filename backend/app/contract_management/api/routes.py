"""Contract management API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser, ContractAccessUser
from app.config import get_settings
from app.contract_management.api.schemas import (
    CommercialValidationRequest,
    ComplianceOverrideRequest,
    ContractConfigRequest,
    ContractRequestListResponse,
    ContractRequestResponse,
    ContractResponse,
)
from app.contract_management.application.use_cases.configure_contract import (
    ConfigureContractUseCase,
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
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)

logger = structlog.get_logger()

router = APIRouter(tags=["Contract Management"])


def _cr_to_response(cr) -> ContractRequestResponse:
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
        client_name=cr.client_name,
        mission_description=cr.mission_description,
        commercial_email=cr.commercial_email,
        third_party_id=cr.third_party_id,
        compliance_override=cr.compliance_override,
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

    return ContractRequestListResponse(
        items=[_cr_to_response(cr) for cr in items],
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
    _user_id, role, email = auth
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")

    if role == "commercial" and cr.commercial_email != email:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    return _cr_to_response(cr)


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
    user_id, _role, _email = access
    cr_repo = ContractRequestRepository(db)
    tp_repo = ThirdPartyRepository(db)

    use_case = ValidateCommercialUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        find_or_create_third_party_use_case=None,
    )

    try:
        cr = await use_case.execute(
            ValidateCommercialCommand(
                contract_request_id=contract_request_id,
                third_party_type=body.third_party_type,
                daily_rate=body.daily_rate,
                start_date=body.start_date,
                contact_email=body.contact_email,
                client_name=body.client_name,
                mission_description=body.mission_description,
                mission_location=body.mission_location,
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

    return _cr_to_response(cr)


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
        cr = await use_case.execute(
            contract_request_id, body.model_dump()
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _cr_to_response(cr)


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

    return _cr_to_response(saved)


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

    return _cr_to_response(saved)


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
    """Generate a DOCX contract draft. ADV/admin only."""
    from app.contract_management.application.use_cases.generate_draft import (
        GenerateDraftUseCase,
    )
    from app.contract_management.infrastructure.adapters.docx_contract_generator import (
        DocxContractGenerator,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    s3_service = S3StorageClient(settings)

    use_case = GenerateDraftUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        contract_generator=DocxContractGenerator(),
        s3_service=s3_service,
        settings=settings,
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
    from app.infrastructure.email.sender import EmailService
    from app.third_party.application.use_cases.generate_magic_link import (
        GenerateMagicLinkUseCase,
    )
    from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
        MagicLinkRepository,
    )

    from app.contract_management.application.use_cases.send_draft_to_partner import (
        SendDraftToPartnerUseCase,
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

    return _cr_to_response(cr)


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
    from app.infrastructure.storage.s3_client import S3StorageClient

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    s3_service = S3StorageClient(settings)
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

    return _cr_to_response(cr)


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

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    tp_repo = ThirdPartyRepository(db)
    crm_service = BoondCrmAdapter(BoondClient(settings))

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

    return _cr_to_response(cr)


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
