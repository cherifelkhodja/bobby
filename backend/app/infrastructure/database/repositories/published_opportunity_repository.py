"""Published Opportunity repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import PublishedOpportunity
from app.domain.value_objects.status import OpportunityStatus
from app.infrastructure.database.models import PublishedOpportunityModel


class PublishedOpportunityRepository:
    """Published Opportunity repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: UUID) -> Optional[PublishedOpportunity]:
        """Get published opportunity by ID."""
        result = await self.session.execute(
            select(PublishedOpportunityModel).where(
                PublishedOpportunityModel.id == opportunity_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_boond_id(self, boond_id: str) -> Optional[PublishedOpportunity]:
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
            select(PublishedOpportunityModel).where(
                PublishedOpportunityModel.id == opportunity.id
            )
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
            select(PublishedOpportunityModel).where(
                PublishedOpportunityModel.id == opportunity_id
            )
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
        search: Optional[str] = None,
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

        query = query.offset(skip).limit(limit).order_by(
            PublishedOpportunityModel.created_at.desc()
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_published(self, search: Optional[str] = None) -> int:
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
        result = await self.session.execute(
            select(PublishedOpportunityModel.boond_opportunity_id)
        )
        return {row[0] for row in result.all()}

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
