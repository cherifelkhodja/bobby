"""Opportunity repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Opportunity
from app.infrastructure.database.models import OpportunityModel


class OpportunityRepository:
    """Opportunity repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: UUID) -> Optional[Opportunity]:
        """Get opportunity by ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_external_id(self, external_id: str) -> Optional[Opportunity]:
        """Get opportunity by external BoondManager ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.external_id == external_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """Save opportunity (create or update)."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.external_id = opportunity.external_id
            model.title = opportunity.title
            model.reference = opportunity.reference
            model.start_date = opportunity.start_date
            model.end_date = opportunity.end_date
            model.response_deadline = opportunity.response_deadline
            model.budget = opportunity.budget
            model.manager_name = opportunity.manager_name
            model.manager_email = opportunity.manager_email
            model.manager_boond_id = opportunity.manager_boond_id
            model.client_name = opportunity.client_name
            model.description = opportunity.description
            model.skills = opportunity.skills
            model.location = opportunity.location
            model.is_active = opportunity.is_active
            model.is_shared = opportunity.is_shared
            model.owner_id = opportunity.owner_id
            model.synced_at = opportunity.synced_at
            model.updated_at = datetime.utcnow()
        else:
            model = OpportunityModel(
                id=opportunity.id,
                external_id=opportunity.external_id,
                title=opportunity.title,
                reference=opportunity.reference,
                start_date=opportunity.start_date,
                end_date=opportunity.end_date,
                response_deadline=opportunity.response_deadline,
                budget=opportunity.budget,
                manager_name=opportunity.manager_name,
                manager_email=opportunity.manager_email,
                manager_boond_id=opportunity.manager_boond_id,
                client_name=opportunity.client_name,
                description=opportunity.description,
                skills=opportunity.skills,
                location=opportunity.location,
                is_active=opportunity.is_active,
                is_shared=opportunity.is_shared,
                owner_id=opportunity.owner_id,
                synced_at=opportunity.synced_at,
                created_at=opportunity.created_at,
                updated_at=opportunity.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def save_many(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Save multiple opportunities."""
        saved = []
        for opp in opportunities:
            saved.append(await self.save(opp))
        return saved

    async def delete(self, opportunity_id: UUID) -> bool:
        """Delete opportunity by ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_active(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> list[Opportunity]:
        """List active opportunities with pagination and optional search."""
        query = select(OpportunityModel).where(OpportunityModel.is_active == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        query = query.offset(skip).limit(limit).order_by(OpportunityModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_active(self, search: Optional[str] = None) -> int:
        """Count active opportunities."""
        query = select(func.count(OpportunityModel.id)).where(
            OpportunityModel.is_active == True
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_last_sync_time(self) -> Optional[datetime]:
        """Get the most recent sync time."""
        result = await self.session.execute(
            select(func.max(OpportunityModel.synced_at))
        )
        return result.scalar()

    async def list_shared(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> list[Opportunity]:
        """List shared opportunities available for cooptation."""
        query = select(OpportunityModel).where(
            OpportunityModel.is_active == True,
            OpportunityModel.is_shared == True,
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        query = query.offset(skip).limit(limit).order_by(OpportunityModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_shared(self, search: Optional[str] = None) -> int:
        """Count shared opportunities."""
        query = select(func.count(OpportunityModel.id)).where(
            OpportunityModel.is_active == True,
            OpportunityModel.is_shared == True,
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def list_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """List opportunities owned by a specific user (commercial)."""
        query = (
            select(OpportunityModel)
            .where(OpportunityModel.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(OpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count opportunities owned by a specific user."""
        result = await self.session.execute(
            select(func.count(OpportunityModel.id)).where(
                OpportunityModel.owner_id == owner_id
            )
        )
        return result.scalar() or 0

    async def list_by_manager_boond_id(
        self,
        manager_boond_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """List opportunities managed by a specific manager (via BoondManager ID)."""
        query = (
            select(OpportunityModel)
            .where(OpportunityModel.manager_boond_id == manager_boond_id)
            .offset(skip)
            .limit(limit)
            .order_by(OpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: OpportunityModel) -> Opportunity:
        """Convert model to entity."""
        return Opportunity(
            id=model.id,
            external_id=model.external_id,
            title=model.title,
            reference=model.reference,
            start_date=model.start_date,
            end_date=model.end_date,
            response_deadline=model.response_deadline,
            budget=model.budget,
            manager_name=model.manager_name,
            manager_email=model.manager_email,
            manager_boond_id=model.manager_boond_id,
            client_name=model.client_name,
            description=model.description,
            skills=model.skills or [],
            location=model.location,
            is_active=model.is_active,
            is_shared=model.is_shared,
            owner_id=model.owner_id,
            synced_at=model.synced_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
