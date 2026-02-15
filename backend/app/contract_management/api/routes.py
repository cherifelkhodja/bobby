"""Contract management API routes."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser
from app.contract_management.api.schemas import (
    CommercialValidationRequest,
    ComplianceOverrideRequest,
    ContractConfigRequest,
    ContractRequestListResponse,
    ContractRequestResponse,
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
    user_id: AdvOrAdminUser,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List contract requests with optional status filter. ADV/admin only."""
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
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a contract request by ID. ADV/admin only."""
    cr_repo = ContractRequestRepository(db)
    cr = await cr_repo.get_by_id(contract_request_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Demande de contrat non trouvée.")
    return _cr_to_response(cr)


@router.post(
    "/{contract_request_id}/validate-commercial",
    response_model=ContractRequestResponse,
    summary="Validate commercial information",
)
async def validate_commercial(
    contract_request_id: UUID,
    body: CommercialValidationRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Apply commercial validation to a contract request. ADV/admin only."""
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
