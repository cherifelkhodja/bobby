"""Published opportunity use cases."""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from app.application.read_models.published_opportunity import (
    AnonymizedPreviewReadModel,
    BoondOpportunityDetailReadModel,
    BoondOpportunityListReadModel,
    BoondOpportunityReadModel,
    PublishedOpportunityListReadModel,
    PublishedOpportunityReadModel,
)
from app.domain.entities import PublishedOpportunity
from app.domain.value_objects.status import OpportunityStatus
from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.database.repositories import PublishedOpportunityRepository


class GetMyBoondOpportunitiesUseCase:
    """Use case for fetching opportunities where user is main manager."""

    def __init__(
        self,
        boond_client: BoondClient,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._boond_client = boond_client
        self._published_repository = published_opportunity_repository

    async def execute(
        self,
        manager_boond_id: Optional[str] = None,
        is_admin: bool = False,
    ) -> BoondOpportunityListReadModel:
        """Fetch opportunities from BoondManager.

        Args:
            manager_boond_id: The user's BoondManager resource ID.
            is_admin: If True, fetch ALL opportunities (admin view).

        Returns:
            List of Boond opportunities with publication status.

        Raises:
            ValueError: If manager_boond_id is not set and user is not admin.
        """
        if not is_admin and not manager_boond_id:
            raise ValueError("L'utilisateur n'a pas d'identifiant BoondManager configuré")

        # Fetch opportunities from Boond
        boond_opportunities = await self._boond_client.get_manager_opportunities(
            manager_boond_id=manager_boond_id,
            fetch_all=is_admin,
        )

        # Get already published IDs
        published_ids = await self._published_repository.get_published_boond_ids()

        # Build read models
        items = [
            BoondOpportunityReadModel(
                id=opp["id"],
                title=opp["title"],
                reference=opp["reference"],
                description=opp.get("description"),
                start_date=opp.get("start_date"),
                end_date=opp.get("end_date"),
                company_name=opp.get("company_name"),
                state=opp.get("state"),
                state_name=opp.get("state_name"),
                state_color=opp.get("state_color"),
                manager_id=opp.get("manager_id"),
                manager_name=opp.get("manager_name"),
                is_published=opp["id"] in published_ids,
            )
            for opp in boond_opportunities
        ]

        return BoondOpportunityListReadModel(
            items=items,
            total=len(items),
        )


class GetBoondOpportunityDetailUseCase:
    """Use case for fetching detailed opportunity information from Boond."""

    def __init__(
        self,
        boond_client: BoondClient,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._boond_client = boond_client
        self._published_repository = published_opportunity_repository

    async def execute(self, opportunity_id: str) -> BoondOpportunityDetailReadModel:
        """Fetch detailed opportunity information from BoondManager.

        Uses the /opportunities/{id}/information endpoint to get full details
        including description and criteria.

        Args:
            opportunity_id: The BoondManager opportunity ID.

        Returns:
            Detailed opportunity information.
        """
        # Fetch from Boond
        opp = await self._boond_client.get_opportunity_information(opportunity_id)

        # Check if already published
        is_published = await self._published_repository.exists_by_boond_id(opportunity_id)

        return BoondOpportunityDetailReadModel(
            id=opp["id"],
            title=opp["title"],
            reference=opp["reference"],
            description=opp.get("description"),
            criteria=opp.get("criteria"),
            expertise_area=opp.get("expertise_area"),
            place=opp.get("place"),
            duration=opp.get("duration"),
            start_date=opp.get("start_date"),
            end_date=opp.get("end_date"),
            closing_date=opp.get("closing_date"),
            answer_date=opp.get("answer_date"),
            company_id=opp.get("company_id"),
            company_name=opp.get("company_name"),
            manager_id=opp.get("manager_id"),
            manager_name=opp.get("manager_name"),
            contact_id=opp.get("contact_id"),
            contact_name=opp.get("contact_name"),
            agency_id=opp.get("agency_id"),
            agency_name=opp.get("agency_name"),
            state=opp.get("state"),
            state_name=opp.get("state_name"),
            state_color=opp.get("state_color"),
            is_published=is_published,
        )


class AnonymizeOpportunityUseCase:
    """Use case for anonymizing an opportunity with AI."""

    def __init__(
        self,
        boond_client: BoondClient,
        anonymizer: GeminiAnonymizer,
    ) -> None:
        self._boond_client = boond_client
        self._anonymizer = anonymizer

    async def execute(
        self,
        title: str,
        description: str,
        boond_opportunity_id: str,
        model_name: Optional[str] = None,
    ) -> AnonymizedPreviewReadModel:
        """Anonymize opportunity title and description.

        Args:
            title: Original opportunity title.
            description: Original opportunity description.
            boond_opportunity_id: The Boond opportunity ID.
            model_name: Gemini model to use (optional, uses configured default).

        Returns:
            Preview of anonymized content.
        """
        # Anonymize using Gemini
        anonymized = await self._anonymizer.anonymize(
            title=title,
            description=description or "",
            model_name=model_name,
        )

        return AnonymizedPreviewReadModel(
            boond_opportunity_id=boond_opportunity_id,
            original_title=title,
            anonymized_title=anonymized.title,
            anonymized_description=anonymized.description,
            skills=anonymized.skills,
        )


class PublishOpportunityUseCase:
    """Use case for publishing an anonymized opportunity."""

    def __init__(
        self,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._repository = published_opportunity_repository

    async def execute(
        self,
        boond_opportunity_id: str,
        title: str,
        description: str,
        skills: list[str],
        original_title: str,
        original_data: Optional[dict[str, Any]],
        end_date: Optional[date],
        publisher_id: UUID,
    ) -> PublishedOpportunityReadModel:
        """Publish an anonymized opportunity.

        Args:
            boond_opportunity_id: Boond opportunity ID (for anti-duplicate).
            title: Anonymized title.
            description: Anonymized description.
            skills: List of extracted skills.
            original_title: Original title (for internal reference).
            original_data: Original Boond data (backup).
            end_date: Opportunity end date.
            publisher_id: ID of the user publishing.

        Returns:
            Published opportunity read model.

        Raises:
            ValueError: If opportunity already published.
        """
        # Check if already published
        if await self._repository.exists_by_boond_id(boond_opportunity_id):
            raise ValueError("Cette opportunité a déjà été publiée")

        # Create entity
        opportunity = PublishedOpportunity(
            boond_opportunity_id=boond_opportunity_id,
            title=title,
            description=description,
            skills=skills,
            original_title=original_title,
            original_data=original_data,
            end_date=end_date,
            published_by=publisher_id,
            status=OpportunityStatus.PUBLISHED,
        )

        # Save
        saved = await self._repository.save(opportunity)

        return self._to_read_model(saved)

    def _to_read_model(
        self, opportunity: PublishedOpportunity
    ) -> PublishedOpportunityReadModel:
        return PublishedOpportunityReadModel(
            id=str(opportunity.id),
            boond_opportunity_id=opportunity.boond_opportunity_id,
            title=opportunity.title,
            description=opportunity.description,
            skills=opportunity.skills,
            end_date=opportunity.end_date,
            status=str(opportunity.status),
            status_display=opportunity.status.display_name,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )


class ListPublishedOpportunitiesUseCase:
    """Use case for listing published opportunities."""

    def __init__(
        self,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._repository = published_opportunity_repository

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> PublishedOpportunityListReadModel:
        """List published opportunities with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            search: Optional search term.

        Returns:
            Paginated list of published opportunities.
        """
        skip = (page - 1) * page_size

        opportunities = await self._repository.list_published(
            skip=skip,
            limit=page_size,
            search=search,
        )
        total = await self._repository.count_published(search=search)

        items = [self._to_read_model(opp) for opp in opportunities]

        return PublishedOpportunityListReadModel(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _to_read_model(
        self, opportunity: PublishedOpportunity
    ) -> PublishedOpportunityReadModel:
        return PublishedOpportunityReadModel(
            id=str(opportunity.id),
            boond_opportunity_id=opportunity.boond_opportunity_id,
            title=opportunity.title,
            description=opportunity.description,
            skills=opportunity.skills,
            end_date=opportunity.end_date,
            status=str(opportunity.status),
            status_display=opportunity.status.display_name,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )


class GetPublishedOpportunityUseCase:
    """Use case for getting a single published opportunity."""

    def __init__(
        self,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._repository = published_opportunity_repository

    async def execute(self, opportunity_id: UUID) -> Optional[PublishedOpportunityReadModel]:
        """Get published opportunity by ID.

        Args:
            opportunity_id: UUID of the published opportunity.

        Returns:
            Published opportunity or None if not found.
        """
        opportunity = await self._repository.get_by_id(opportunity_id)

        if not opportunity:
            return None

        return PublishedOpportunityReadModel(
            id=str(opportunity.id),
            boond_opportunity_id=opportunity.boond_opportunity_id,
            title=opportunity.title,
            description=opportunity.description,
            skills=opportunity.skills,
            end_date=opportunity.end_date,
            status=str(opportunity.status),
            status_display=opportunity.status.display_name,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )


class CloseOpportunityUseCase:
    """Use case for closing a published opportunity."""

    def __init__(
        self,
        published_opportunity_repository: PublishedOpportunityRepository,
    ) -> None:
        self._repository = published_opportunity_repository

    async def execute(
        self,
        opportunity_id: UUID,
        user_id: UUID,
    ) -> PublishedOpportunityReadModel:
        """Close a published opportunity.

        Args:
            opportunity_id: UUID of the opportunity to close.
            user_id: ID of the user closing the opportunity.

        Returns:
            Updated opportunity read model.

        Raises:
            ValueError: If opportunity not found or user not authorized.
        """
        opportunity = await self._repository.get_by_id(opportunity_id)

        if not opportunity:
            raise ValueError("Opportunité non trouvée")

        # Only the publisher or admin can close
        # (admin check should be done at API level)
        if opportunity.published_by != user_id:
            raise ValueError("Non autorisé à fermer cette opportunité")

        # Close
        opportunity.close()

        # Save
        saved = await self._repository.save(opportunity)

        return PublishedOpportunityReadModel(
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
