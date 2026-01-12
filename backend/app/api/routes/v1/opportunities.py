"""Opportunity endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.opportunity import OpportunityListResponse, OpportunityResponse
from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)
from app.dependencies import AppSettings, Boond, DbSession, RedisClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository

router = APIRouter()


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    db: DbSession,
    redis: RedisClient,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    """List available opportunities with pagination."""
    opportunity_repo = OpportunityRepository(db)
    cache_service = CacheService(redis)

    use_case = ListOpportunitiesUseCase(opportunity_repo, cache_service)
    result = await use_case.execute(page=page, page_size=page_size, search=search)

    return OpportunityListResponse(
        items=[OpportunityResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
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
        raise HTTPException(status_code=404, detail="Opportunity not found")

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
        client_name=opportunity.client_name,
        description=opportunity.description,
        skills=opportunity.skills,
        location=opportunity.location,
        is_open=opportunity.is_open,
        days_until_deadline=opportunity.days_until_deadline,
        synced_at=opportunity.synced_at,
        created_at=opportunity.created_at,
    )


@router.post("/sync")
async def sync_opportunities(
    db: DbSession,
    redis: RedisClient,
    boond: Boond,
    settings: AppSettings,
):
    """Sync opportunities from BoondManager (admin only)."""
    if not settings.FEATURE_BOOND_SYNC:
        raise HTTPException(status_code=404, detail="Feature not available")

    opportunity_repo = OpportunityRepository(db)
    cache_service = CacheService(redis)

    use_case = SyncOpportunitiesUseCase(boond, opportunity_repo, cache_service)
    count = await use_case.execute()

    return {"message": f"Synced {count} opportunities from BoondManager"}
