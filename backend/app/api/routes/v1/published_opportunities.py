"""Published opportunity endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import AdminOrCommercialUser, AdminUser, CurrentUserId

logger = logging.getLogger(__name__)
from app.api.schemas.published_opportunity import (
    AnonymizedPreviewResponse,
    AnonymizeRequest,
    BoondOpportunityDetailResponse,
    BoondOpportunityListResponse,
    BoondOpportunityResponse,
    PublishedOpportunityListResponse,
    PublishedOpportunityResponse,
    PublishRequest,
    UpdatePublishedOpportunityRequest,
)
from app.application.use_cases.published_opportunities import (
    AnonymizeOpportunityUseCase,
    CloseOpportunityUseCase,
    GetBoondOpportunityDetailUseCase,
    GetMyBoondOpportunitiesUseCase,
    GetPublishedOpportunityUseCase,
    ListPublishedOpportunitiesUseCase,
    PublishOpportunityUseCase,
    ReopenOpportunityUseCase,
)
from app.dependencies import AppSettings, AppSettingsSvc, Boond, DbSession
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
    """List Boond opportunities.

    For admins: returns ALL opportunities from BoondManager.
    For commercials: returns only opportunities where user is main manager.

    Requires admin or commercial role.
    """
    # Get user's boond_resource_id and role
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    is_admin = user and user.role == "admin"

    # Non-admins need a boond_resource_id
    if not is_admin and (not user or not user.boond_resource_id):
        raise HTTPException(
            status_code=400,
            detail="Vous n'avez pas d'identifiant BoondManager configuré",
        )

    published_repo = PublishedOpportunityRepository(db)

    use_case = GetMyBoondOpportunitiesUseCase(boond, published_repo)

    try:
        result = await use_case.execute(
            manager_boond_id=user.boond_resource_id if user else None,
            is_admin=is_admin,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BoondOpportunityListResponse(
        items=[BoondOpportunityResponse(**item.model_dump()) for item in result.items],
        total=result.total,
    )


@router.get("/my-boond/{opportunity_id}", response_model=BoondOpportunityDetailResponse)
async def get_boond_opportunity_detail(
    opportunity_id: str,
    db: DbSession,
    boond: Boond,
    user_id: AdminOrCommercialUser,
):
    """Get detailed information for a Boond opportunity.

    Fetches full opportunity details including description and criteria
    from the /opportunities/{id}/information endpoint.

    Requires admin or commercial role.
    """
    published_repo = PublishedOpportunityRepository(db)

    use_case = GetBoondOpportunityDetailUseCase(boond, published_repo)

    try:
        result = await use_case.execute(opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BoondOpportunityDetailResponse(**result.model_dump())


@router.post("/anonymize", response_model=AnonymizedPreviewResponse)
async def anonymize_opportunity(
    request: AnonymizeRequest,
    settings: AppSettings,
    app_settings_svc: AppSettingsSvc,
    user_id: AdminOrCommercialUser,
):
    """Anonymize an opportunity using AI.

    Returns a preview of the anonymized content.
    Requires admin or commercial role.
    """
    # Get configured model from database settings
    model_name = await app_settings_svc.get_gemini_model()

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
            model_name=model_name,
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
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Cette opportunité a déjà été publiée",
        )
    except Exception:
        logger.exception("Error publishing opportunity %s", request.boond_opportunity_id)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la publication de l'opportunité",
        )

    return PublishedOpportunityResponse(**result.model_dump())


@router.get("", response_model=PublishedOpportunityListResponse)
async def list_published_opportunities(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
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
        items=[PublishedOpportunityResponse(**item.model_dump()) for item in result.items],
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


@router.patch("/{opportunity_id}", response_model=PublishedOpportunityResponse)
async def update_published_opportunity(
    opportunity_id: UUID,
    request: UpdatePublishedOpportunityRequest,
    db: DbSession,
    user_id: AdminOrCommercialUser,
):
    """Update a published opportunity.

    Can only be updated by the publisher or an admin.
    Requires admin or commercial role.
    """
    published_repo = PublishedOpportunityRepository(db)
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(user_id)
    is_admin = user and user.role == "admin"

    opportunity = await published_repo.get_by_id(opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    if not is_admin and opportunity.published_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez modifier que vos propres opportunités",
        )

    opportunity.update_content(
        title=request.title,
        description=request.description,
        skills=request.skills,
        end_date=request.end_date,
    )

    saved = await published_repo.save(opportunity)

    return PublishedOpportunityResponse(
        id=str(saved.id),
        boond_opportunity_id=saved.boond_opportunity_id,
        title=saved.title,
        description=saved.description,
        skills=saved.skills,
        end_date=saved.end_date,
        status=str(saved.status),
        status_display=saved.status.display_name,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


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


@router.patch("/{opportunity_id}/reopen", response_model=PublishedOpportunityResponse)
async def reopen_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    user_id: AdminOrCommercialUser,
):
    """Reopen a closed published opportunity.

    Can only be reopened by the publisher or an admin.
    Requires admin or commercial role.
    """
    published_repo = PublishedOpportunityRepository(db)
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(user_id)
    is_admin = user and user.role == "admin"

    use_case = ReopenOpportunityUseCase(published_repo)

    try:
        opportunity = await published_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunité non trouvée")

        if not is_admin and opportunity.published_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez réactiver que vos propres opportunités",
            )

        result = await use_case.execute(
            opportunity_id=opportunity_id,
            user_id=opportunity.published_by if is_admin else user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PublishedOpportunityResponse(**result.model_dump())
<<<<<<< HEAD


@router.delete("/{opportunity_id}", status_code=204)
async def delete_published_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    user_id: AdminUser,
):
    """Delete a published opportunity permanently (admin only)."""
    published_repo = PublishedOpportunityRepository(db)

    deleted = await published_repo.delete(opportunity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")
