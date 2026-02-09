"""Opportunity endpoints."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from app.api.schemas.opportunity import OpportunityListResponse, OpportunityResponse
from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)
from app.dependencies import AppSettings, Boond, DbSession, RedisClient
from app.domain.value_objects import UserRole
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository, UserRepository
from app.infrastructure.security.jwt import decode_token

router = APIRouter()


def _opportunity_to_response(opportunity) -> OpportunityResponse:
    """Convert opportunity entity to response."""
    return OpportunityResponse(
        id=str(opportunity.id),
        external_id=opportunity.external_id,
        title=opportunity.title,
        reference=opportunity.reference,
        budget=opportunity.budget,
        start_date=opportunity.start_date,
        end_date=opportunity.end_date,
        response_deadline=opportunity.response_deadline,
        manager_name=opportunity.manager_name,
        manager_boond_id=opportunity.manager_boond_id,
        client_name=opportunity.client_name,
        description=opportunity.description,
        skills=opportunity.skills,
        location=opportunity.location,
        is_open=opportunity.is_open,
        is_shared=opportunity.is_shared,
        owner_id=str(opportunity.owner_id) if opportunity.owner_id else None,
        days_until_deadline=opportunity.days_until_deadline,
        synced_at=opportunity.synced_at,
        created_at=opportunity.created_at,
    )


async def get_current_user(db: DbSession, authorization: str):
    """Get current user from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    return user


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    db: DbSession,
    redis: RedisClient,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    shared_only: bool = Query(False, description="Only show shared opportunities"),
):
    """List available opportunities with pagination.

    If shared_only=True, only returns opportunities marked as shared for cooptation.
    """
    opportunity_repo = OpportunityRepository(db)
    cache_service = CacheService(redis)

    if shared_only:
        # List only shared opportunities (for users to coopt)
        skip = (page - 1) * page_size
        opportunities = await opportunity_repo.list_shared(
            skip=skip, limit=page_size, search=search
        )
        total = await opportunity_repo.count_shared(search=search)

        return OpportunityListResponse(
            items=[_opportunity_to_response(opp) for opp in opportunities],
            total=total,
            page=page,
            page_size=page_size,
        )

    # Standard listing (all active opportunities)
    use_case = ListOpportunitiesUseCase(opportunity_repo, cache_service)
    result = await use_case.execute(page=page, page_size=page_size, search=search)

    return OpportunityListResponse(
        items=[OpportunityResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/my", response_model=OpportunityListResponse)
async def list_my_opportunities(
    db: DbSession,
    authorization: str = Header(default=""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List opportunities owned by the current commercial user."""
    user = await get_current_user(db, authorization)

    if user.role not in (UserRole.COMMERCIAL, UserRole.ADMIN):
        raise HTTPException(
            status_code=403, detail="Seuls les commerciaux peuvent accéder à leurs opportunités"
        )

    opportunity_repo = OpportunityRepository(db)
    skip = (page - 1) * page_size

    # For commercials, list opportunities they own
    # For admins, they can use /my to see opportunities assigned to them
    opportunities = await opportunity_repo.list_by_owner(
        owner_id=user.id, skip=skip, limit=page_size
    )
    total = await opportunity_repo.count_by_owner(owner_id=user.id)

    return OpportunityListResponse(
        items=[_opportunity_to_response(opp) for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: UUID,
    db: DbSession,
):
    """Get opportunity details."""
    opportunity_repo = OpportunityRepository(db)

    opportunity = await opportunity_repo.get_by_id(opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    return _opportunity_to_response(opportunity)


@router.post("/{opportunity_id}/share")
async def share_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Share an opportunity for cooptation (commercial/admin only)."""
    user = await get_current_user(db, authorization)

    if user.role not in (UserRole.COMMERCIAL, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Seuls les commerciaux et admins peuvent partager des opportunités",
        )

    opportunity_repo = OpportunityRepository(db)
    opportunity = await opportunity_repo.get_by_id(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    # Check ownership for commercials (admins can share any)
    if user.role == UserRole.COMMERCIAL:
        if opportunity.owner_id and opportunity.owner_id != user.id:
            raise HTTPException(
                status_code=403, detail="Vous ne pouvez partager que vos propres opportunités"
            )
        # Assign ownership if not set
        if not opportunity.owner_id:
            opportunity.assign_owner(user.id)

    opportunity.share()
    await opportunity_repo.save(opportunity)

    return {"message": "Opportunité partagée pour cooptation", "is_shared": True}


@router.post("/{opportunity_id}/unshare")
async def unshare_opportunity(
    opportunity_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Remove an opportunity from cooptation sharing (commercial/admin only)."""
    user = await get_current_user(db, authorization)

    if user.role not in (UserRole.COMMERCIAL, UserRole.ADMIN):
        raise HTTPException(
            status_code=403, detail="Seuls les commerciaux et admins peuvent gérer les opportunités"
        )

    opportunity_repo = OpportunityRepository(db)
    opportunity = await opportunity_repo.get_by_id(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    # Check ownership for commercials (admins can unshare any)
    if user.role == UserRole.COMMERCIAL and opportunity.owner_id != user.id:
        raise HTTPException(
            status_code=403, detail="Vous ne pouvez gérer que vos propres opportunités"
        )

    opportunity.unshare()
    await opportunity_repo.save(opportunity)

    return {"message": "Opportunité retirée de la cooptation", "is_shared": False}


@router.post("/{opportunity_id}/assign")
async def assign_opportunity_owner(
    opportunity_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
    owner_id: UUID | None = None,
):
    """Assign an owner to an opportunity (admin only, or commercial assigns to self)."""
    user = await get_current_user(db, authorization)

    opportunity_repo = OpportunityRepository(db)
    opportunity = await opportunity_repo.get_by_id(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    # Admins can assign to anyone, commercials can only assign to themselves
    if user.role == UserRole.ADMIN:
        new_owner_id = owner_id if owner_id else user.id
    elif user.role == UserRole.COMMERCIAL:
        if owner_id and owner_id != user.id:
            raise HTTPException(
                status_code=403, detail="Vous ne pouvez vous assigner que vous-même"
            )
        new_owner_id = user.id
    else:
        raise HTTPException(status_code=403, detail="Action non autorisée")

    opportunity.assign_owner(new_owner_id)
    await opportunity_repo.save(opportunity)

    return {"message": "Propriétaire assigné", "owner_id": str(new_owner_id)}


@router.post("/sync")
async def sync_opportunities(
    db: DbSession,
    redis: RedisClient,
    boond: Boond,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Sync opportunities from BoondManager (admin only)."""
    user = await get_current_user(db, authorization)

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Accès administrateur requis")

    if not settings.FEATURE_BOOND_SYNC:
        raise HTTPException(status_code=404, detail="Fonctionnalité non disponible")

    opportunity_repo = OpportunityRepository(db)
    cache_service = CacheService(redis)

    use_case = SyncOpportunitiesUseCase(boond, opportunity_repo, cache_service)
    count = await use_case.execute()

    return {"message": f"{count} opportunités synchronisées depuis BoondManager"}
