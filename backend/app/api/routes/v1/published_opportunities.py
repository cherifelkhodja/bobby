"""Published opportunity endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import AdminOrCommercialUser, CurrentUserId
from app.api.schemas.published_opportunity import (
    AnonymizedPreviewResponse,
    AnonymizeRequest,
    BoondOpportunityListResponse,
    BoondOpportunityResponse,
    PublishedOpportunityListResponse,
    PublishedOpportunityResponse,
    PublishRequest,
)
from app.application.use_cases.published_opportunities import (
    AnonymizeOpportunityUseCase,
    CloseOpportunityUseCase,
    GetMyBoondOpportunitiesUseCase,
    GetPublishedOpportunityUseCase,
    ListPublishedOpportunitiesUseCase,
    PublishOpportunityUseCase,
)
from app.dependencies import AppSettings, Boond, DbSession
from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer
from app.infrastructure.database.repositories import (
    PublishedOpportunityRepository,
    UserRepository,
)

router = APIRouter()


@router.get("/my-boond", response_model=BoondOpportunityListResponse)
async def list_my_boond_opportunities(
    db: DbSession,
    boond: Boond,
    user_id: AdminOrCommercialUser,
):
    """List Boond opportunities where current user is main manager.

    Requires admin or commercial role.
    """
    # Get user's boond_resource_id
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.boond_resource_id:
        raise HTTPException(
            status_code=400,
            detail="Vous n'avez pas d'identifiant BoondManager configuré",
        )

    published_repo = PublishedOpportunityRepository(db)

    use_case = GetMyBoondOpportunitiesUseCase(boond, published_repo)

    try:
        result = await use_case.execute(user.boond_resource_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BoondOpportunityListResponse(
        items=[
            BoondOpportunityResponse(**item.model_dump())
            for item in result.items
        ],
        total=result.total,
    )


@router.post("/anonymize", response_model=AnonymizedPreviewResponse)
async def anonymize_opportunity(
    request: AnonymizeRequest,
    settings: AppSettings,
    user_id: AdminOrCommercialUser,
):
    """Anonymize an opportunity using AI.

    Returns a preview of the anonymized content.
    Requires admin or commercial role.
    """
    anonymizer = GeminiAnonymizer(settings)

    use_case = AnonymizeOpportunityUseCase(
        boond_client=None,  # Not needed, we pass data directly
        anonymizer=anonymizer,
    )

    try:
        result = await use_case.execute(
            title=request.title,
            description=request.description or "",
            boond_opportunity_id=request.boond_opportunity_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AnonymizedPreviewResponse(
        boond_opportunity_id=result.boond_opportunity_id,
        original_title=result.original_title,
        anonymized_title=result.anonymized_title,
        anonymized_description=result.anonymized_description,
        skills=result.skills,
    )


@router.post("/publish", response_model=PublishedOpportunityResponse)
async def publish_opportunity(
    request: PublishRequest,
    db: DbSession,
    user_id: AdminOrCommercialUser,
):
    """Publish an anonymized opportunity.

    Creates a new published opportunity visible to all users.
    Requires admin or commercial role.
    """
    published_repo = PublishedOpportunityRepository(db)

    use_case = PublishOpportunityUseCase(published_repo)

    try:
        result = await use_case.execute(
            boond_opportunity_id=request.boond_opportunity_id,
            title=request.title,
            description=request.description,
            skills=request.skills,
            original_title=request.original_title,
            original_data=request.original_data,
            end_date=request.end_date,
            publisher_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PublishedOpportunityResponse(**result.model_dump())


@router.get("", response_model=PublishedOpportunityListResponse)
async def list_published_opportunities(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    """List published opportunities.

    Available to all authenticated users.
    """
    published_repo = PublishedOpportunityRepository(db)

    use_case = ListPublishedOpportunitiesUseCase(published_repo)

    result = await use_case.execute(
        page=page,
        page_size=page_size,
        search=search,
    )

    return PublishedOpportunityListResponse(
        items=[
            PublishedOpportunityResponse(**item.model_dump())
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/{opportunity_id}", response_model=PublishedOpportunityResponse)
async def get_published_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    user_id: CurrentUserId,
):
    """Get a published opportunity by ID.

    Available to all authenticated users.
    """
    published_repo = PublishedOpportunityRepository(db)

    use_case = GetPublishedOpportunityUseCase(published_repo)

    result = await use_case.execute(opportunity_id)

    if not result:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    return PublishedOpportunityResponse(**result.model_dump())


@router.patch("/{opportunity_id}/close", response_model=PublishedOpportunityResponse)
async def close_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    user_id: AdminOrCommercialUser,
):
    """Close a published opportunity.

    Can only be closed by the publisher or an admin.
    Requires admin or commercial role.
    """
    published_repo = PublishedOpportunityRepository(db)
    user_repo = UserRepository(db)

    # Check if admin (can close any)
    user = await user_repo.get_by_id(user_id)
    is_admin = user and user.role == "admin"

    use_case = CloseOpportunityUseCase(published_repo)

    try:
        # If admin, use the opportunity's publisher_id check will still apply
        # but we override by checking admin status
        opportunity = await published_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunité non trouvée")

        # Admin can close any, commercial only their own
        if not is_admin and opportunity.published_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez fermer que vos propres opportunités",
            )

        result = await use_case.execute(
            opportunity_id=opportunity_id,
            user_id=opportunity.published_by if is_admin else user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PublishedOpportunityResponse(**result.model_dump())
