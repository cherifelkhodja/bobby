"""Cooptation endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from app.api.schemas.cooptation import (
    CooptationListResponse,
    CooptationResponse,
    CooptationStatsResponse,
    CreateCooptationRequest,
    UpdateCooptationStatusRequest,
)
from app.application.use_cases.cooptations import (
    CreateCooptationCommand,
    CreateCooptationUseCase,
    GetCooptationStatsUseCase,
    GetCooptationUseCase,
    ListCooptationsUseCase,
    UpdateCooptationStatusUseCase,
)
from app.dependencies import AppSettings, Boond, DbSession
from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    OpportunityNotFoundError,
)
from app.domain.value_objects import CooptationStatus
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    OpportunityRepository,
    PublishedOpportunityRepository,
    UserRepository,
)
from app.infrastructure.email.sender import EmailService
from app.infrastructure.security.jwt import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_id_from_auth(authorization: str) -> UUID:
    """Extract user ID from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    return UUID(payload.sub)


@router.post("", response_model=CooptationResponse, status_code=201)
async def create_cooptation(
    request: CreateCooptationRequest,
    db: DbSession,
    boond: Boond,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Create a new cooptation (propose a candidate for an opportunity)."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    candidate_repo = CandidateRepository(db)
    opportunity_repo = OpportunityRepository(db)
    published_opportunity_repo = PublishedOpportunityRepository(db)
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = CreateCooptationUseCase(
        cooptation_repo,
        candidate_repo,
        opportunity_repo,
        published_opportunity_repo,
        user_repo,
        boond,
        email_service,
    )

    command = CreateCooptationCommand(
        opportunity_id=UUID(request.opportunity_id),
        submitter_id=user_id,
        candidate_first_name=request.candidate_first_name,
        candidate_last_name=request.candidate_last_name,
        candidate_email=request.candidate_email,
        candidate_civility=request.candidate_civility,
        candidate_phone=request.candidate_phone,
        candidate_daily_rate=request.candidate_daily_rate,
        candidate_note=request.candidate_note,
    )

    try:
        result = await use_case.execute(command)
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")
    except CandidateAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("Error creating cooptation for opportunity %s", request.opportunity_id)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la cooptation",
        )

    return CooptationResponse(**result.model_dump())


@router.get("", response_model=CooptationListResponse)
async def list_cooptations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    opportunity_id: str | None = Query(None),
    authorization: str = Header(default=""),
):
    """List all cooptations with optional filters."""
    get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)

    status_filter = CooptationStatus(status) if status else None
    opp_id = UUID(opportunity_id) if opportunity_id else None

    # Resolve published opportunity ID to actual opportunity ID.
    # Cooptations reference the synced opportunity (from Boond), which may
    # have a different UUID than the published_opportunity.id.
    if opp_id:
        published_repo = PublishedOpportunityRepository(db)
        published = await published_repo.get_by_id(opp_id)
        if published:
            opportunity_repo = OpportunityRepository(db)
            opp = await opportunity_repo.get_by_external_id(
                published.boond_opportunity_id
            )
            if opp:
                opp_id = opp.id

    use_case = ListCooptationsUseCase(cooptation_repo, user_repo)
    result = await use_case.execute(
        page=page,
        page_size=page_size,
        status=status_filter,
        opportunity_id=opp_id,
    )

    return CooptationListResponse(
        items=[CooptationResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/me", response_model=CooptationListResponse)
async def list_my_cooptations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    authorization: str = Header(default=""),
):
    """List current user's cooptations."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)

    use_case = ListCooptationsUseCase(cooptation_repo, user_repo)
    result = await use_case.execute(
        page=page,
        page_size=page_size,
        submitter_id=user_id,
    )

    return CooptationListResponse(
        items=[CooptationResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/me/stats", response_model=CooptationStatsResponse)
async def get_my_stats(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get current user's cooptation statistics."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationStatsUseCase(cooptation_repo)
    result = await use_case.execute(submitter_id=user_id)

    return CooptationStatsResponse(**result.model_dump())


@router.get("/stats", response_model=CooptationStatsResponse)
async def get_all_stats(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get overall cooptation statistics (admin view)."""
    # In production, would check for admin role
    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationStatsUseCase(cooptation_repo)
    result = await use_case.execute()

    return CooptationStatsResponse(**result.model_dump())


@router.get("/{cooptation_id}", response_model=CooptationResponse)
async def get_cooptation(
    cooptation_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get cooptation details."""
    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationUseCase(cooptation_repo)
    result = await use_case.execute(cooptation_id)

    return CooptationResponse(**result.model_dump())


@router.patch("/{cooptation_id}/status", response_model=CooptationResponse)
async def update_cooptation_status(
    cooptation_id: UUID,
    request: UpdateCooptationStatusRequest,
    db: DbSession,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Update cooptation status (admin only)."""
    user_id = get_user_id_from_auth(authorization)

    # In production, would check for admin role

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = UpdateCooptationStatusUseCase(
        cooptation_repo,
        user_repo,
        email_service,
    )

    new_status = CooptationStatus(request.status)
    result = await use_case.execute(
        cooptation_id=cooptation_id,
        new_status=new_status,
        changed_by=user_id,
        comment=request.comment,
    )

    return CooptationResponse(**result.model_dump())
