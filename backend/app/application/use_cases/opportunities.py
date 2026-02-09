"""Opportunity use cases."""

from app.application.read_models.opportunity import (
    OpportunityListReadModel,
    OpportunityReadModel,
)
from app.domain.entities import Opportunity
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository


class ListOpportunitiesUseCase:
    """Use case for listing opportunities."""

    def __init__(
        self,
        opportunity_repository: OpportunityRepository,
        cache_service: CacheService,
    ) -> None:
        self.opportunity_repository = opportunity_repository
        self.cache_service = cache_service

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> OpportunityListReadModel:
        """List opportunities with pagination and optional search."""
        skip = (page - 1) * page_size

        opportunities = await self.opportunity_repository.list_active(
            skip=skip,
            limit=page_size,
            search=search,
        )
        total = await self.opportunity_repository.count_active(search=search)

        items = [self._to_read_model(opp) for opp in opportunities]

        return OpportunityListReadModel(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _to_read_model(self, opportunity: Opportunity) -> OpportunityReadModel:
        return OpportunityReadModel(
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


class SyncOpportunitiesUseCase:
    """Use case for syncing opportunities from BoondManager."""

    def __init__(
        self,
        boond_client: BoondClient,
        opportunity_repository: OpportunityRepository,
        cache_service: CacheService,
    ) -> None:
        self.boond_client = boond_client
        self.opportunity_repository = opportunity_repository
        self.cache_service = cache_service

    async def execute(self) -> int:
        """
        Sync opportunities from BoondManager.
        Returns the number of opportunities synced.
        """
        # Fetch from BoondManager
        boond_opportunities = await self.boond_client.get_opportunities()

        synced_count = 0

        for boond_opp in boond_opportunities:
            # Check if opportunity already exists
            existing = await self.opportunity_repository.get_by_external_id(boond_opp.external_id)

            if existing:
                # Update existing
                existing.update_from_sync(
                    title=boond_opp.title,
                    start_date=boond_opp.start_date,
                    end_date=boond_opp.end_date,
                    budget=boond_opp.budget,
                    manager_name=boond_opp.manager_name,
                )
                await self.opportunity_repository.save(existing)
            else:
                # Create new
                await self.opportunity_repository.save(boond_opp)

            synced_count += 1

        # Invalidate cache
        await self.cache_service.invalidate_opportunities()

        return synced_count
