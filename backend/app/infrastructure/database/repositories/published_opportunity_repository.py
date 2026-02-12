"""Published Opportunity repository implementation."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import PublishedOpportunity
from app.domain.value_objects.status import OpportunityStatus
from app.infrastructure.database.models import (
    CooptationModel,
    OpportunityModel,
    PublishedOpportunityModel,
)


class PublishedOpportunityRepository:
    """Published Opportunity repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: UUID) -> PublishedOpportunity | None:
        """Get published opportunity by ID."""
        result = await self.session.execute(
            select(PublishedOpportunityModel).where(PublishedOpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_boond_id(self, boond_id: str) -> PublishedOpportunity | None:
        """Get published opportunity by Boond opportunity ID."""
        result = await self.session.execute(
            select(PublishedOpportunityModel).where(
                PublishedOpportunityModel.boond_opportunity_id == boond_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def exists_by_boond_id(self, boond_id: str) -> bool:
        """Check if an opportunity with this Boond ID already exists."""
        result = await self.session.execute(
            select(func.count(PublishedOpportunityModel.id)).where(
                PublishedOpportunityModel.boond_opportunity_id == boond_id
            )
        )
        return (result.scalar() or 0) > 0

    async def save(self, opportunity: PublishedOpportunity) -> PublishedOpportunity:
        """Save published opportunity (create or update)."""
        result = await self.session.execute(
            select(PublishedOpportunityModel).where(PublishedOpportunityModel.id == opportunity.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.boond_opportunity_id = opportunity.boond_opportunity_id
            model.title = opportunity.title
            model.description = opportunity.description
            model.skills = opportunity.skills
            model.original_title = opportunity.original_title
            model.original_data = opportunity.original_data
            model.end_date = opportunity.end_date
            model.status = str(opportunity.status)
            model.published_by = opportunity.published_by
            model.updated_at = datetime.utcnow()
        else:
            model = PublishedOpportunityModel(
                id=opportunity.id,
                boond_opportunity_id=opportunity.boond_opportunity_id,
                title=opportunity.title,
                description=opportunity.description,
                skills=opportunity.skills,
                original_title=opportunity.original_title,
                original_data=opportunity.original_data,
                end_date=opportunity.end_date,
                status=str(opportunity.status),
                published_by=opportunity.published_by,
                created_at=opportunity.created_at,
                updated_at=opportunity.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, opportunity_id: UUID) -> bool:
        """Delete published opportunity by ID."""
        result = await self.session.execute(
            select(PublishedOpportunityModel).where(PublishedOpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_published(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> list[PublishedOpportunity]:
        """List published opportunities visible to consultants."""
        query = select(PublishedOpportunityModel).where(
            PublishedOpportunityModel.status == str(OpportunityStatus.PUBLISHED)
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    PublishedOpportunityModel.title.ilike(search_pattern),
                    PublishedOpportunityModel.description.ilike(search_pattern),
                )
            )

        query = (
            query.offset(skip).limit(limit).order_by(PublishedOpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_published(self, search: str | None = None) -> int:
        """Count published opportunities."""
        query = select(func.count(PublishedOpportunityModel.id)).where(
            PublishedOpportunityModel.status == str(OpportunityStatus.PUBLISHED)
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    PublishedOpportunityModel.title.ilike(search_pattern),
                    PublishedOpportunityModel.description.ilike(search_pattern),
                )
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def list_by_publisher(
        self,
        publisher_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PublishedOpportunity]:
        """List opportunities published by a specific user."""
        query = (
            select(PublishedOpportunityModel)
            .where(PublishedOpportunityModel.published_by == publisher_id)
            .offset(skip)
            .limit(limit)
            .order_by(PublishedOpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_published_boond_ids(self) -> set[str]:
        """Get set of all Boond opportunity IDs that have been published."""
        result = await self.session.execute(select(PublishedOpportunityModel.boond_opportunity_id))
        return {row[0] for row in result.all()}

    async def get_published_boond_data(
        self,
    ) -> dict[str, dict]:
        """Get enriched publication data for all published opportunities.

        Returns a dict mapping boond_opportunity_id to {id, status, cooptations_count}.
        Uses a LEFT JOIN with cooptations to count candidates per opportunity.
        """
        # Join through opportunities table to handle case where cooptation's
        # opportunity_id points to a synced opportunity (different UUID than
        # published_opportunity.id), linked via external_id/boond_opportunity_id.
        query = (
            select(
                PublishedOpportunityModel.boond_opportunity_id,
                PublishedOpportunityModel.id,
                PublishedOpportunityModel.status,
                func.count(CooptationModel.id).label("cooptations_count"),
            )
            .outerjoin(
                OpportunityModel,
                OpportunityModel.external_id
                == PublishedOpportunityModel.boond_opportunity_id,
            )
            .outerjoin(
                CooptationModel,
                CooptationModel.opportunity_id == OpportunityModel.id,
            )
            .group_by(
                PublishedOpportunityModel.boond_opportunity_id,
                PublishedOpportunityModel.id,
                PublishedOpportunityModel.status,
            )
        )
        result = await self.session.execute(query)
        return {
            row.boond_opportunity_id: {
                "id": str(row.id),
                "status": row.status,
                "cooptations_count": row.cooptations_count,
            }
            for row in result.all()
        }

    async def close_expired(self) -> int:
        """Close all published opportunities whose end_date has passed.

        Returns the number of opportunities closed.
        """
        result = await self.session.execute(
            update(PublishedOpportunityModel)
            .where(
                PublishedOpportunityModel.status == str(OpportunityStatus.PUBLISHED),
                PublishedOpportunityModel.end_date.isnot(None),
                PublishedOpportunityModel.end_date < date.today(),
            )
            .values(
                status=str(OpportunityStatus.CLOSED),
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.flush()
        return result.rowcount

    def _to_entity(self, model: PublishedOpportunityModel) -> PublishedOpportunity:
        """Convert model to entity."""
        return PublishedOpportunity(
            id=model.id,
            boond_opportunity_id=model.boond_opportunity_id,
            title=model.title,
            description=model.description,
            skills=model.skills or [],
            original_title=model.original_title,
            original_data=model.original_data,
            end_date=model.end_date,
            status=OpportunityStatus(model.status),
            published_by=model.published_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
