"""Business Lead repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BusinessLead
from app.domain.entities.business_lead import BusinessLeadStatus
from app.infrastructure.database.models import BusinessLeadModel, UserModel


class BusinessLeadRepository:
    """Business Lead repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, lead_id: UUID) -> Optional[BusinessLead]:
        """Get business lead by ID."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, lead: BusinessLead) -> BusinessLead:
        """Save business lead (create or update)."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.title = lead.title
            model.description = lead.description
            model.submitter_id = lead.submitter_id
            model.client_name = lead.client_name
            model.contact_name = lead.contact_name
            model.contact_email = lead.contact_email
            model.contact_phone = lead.contact_phone
            model.estimated_budget = lead.estimated_budget
            model.expected_start_date = lead.expected_start_date
            model.skills_needed = lead.skills_needed
            model.location = lead.location
            model.status = str(lead.status)
            model.rejection_reason = lead.rejection_reason
            model.notes = lead.notes
            model.updated_at = datetime.utcnow()
        else:
            model = BusinessLeadModel(
                id=lead.id,
                title=lead.title,
                description=lead.description,
                submitter_id=lead.submitter_id,
                client_name=lead.client_name,
                contact_name=lead.contact_name,
                contact_email=lead.contact_email,
                contact_phone=lead.contact_phone,
                estimated_budget=lead.estimated_budget,
                expected_start_date=lead.expected_start_date,
                skills_needed=lead.skills_needed,
                location=lead.location,
                status=str(lead.status),
                rejection_reason=lead.rejection_reason,
                notes=lead.notes,
                created_at=lead.created_at,
                updated_at=lead.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, lead_id: UUID) -> bool:
        """Delete business lead by ID."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_by_submitter(
        self,
        submitter_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads by submitter."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .where(BusinessLeadModel.submitter_id == submitter_id)
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_manager(
        self,
        manager_boond_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads visible to a manager (via submitter's manager_boond_id)."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .join(UserModel, BusinessLeadModel.submitter_id == UserModel.id)
            .where(UserModel.manager_boond_id == manager_boond_id)
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_status(
        self,
        status: BusinessLeadStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads by status."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .where(BusinessLeadModel.status == str(status))
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BusinessLeadStatus] = None,
    ) -> list[BusinessLead]:
        """List all business leads with optional status filter."""
        query = select(BusinessLeadModel)

        if status:
            query = query.where(BusinessLeadModel.status == str(status))

        query = query.offset(skip).limit(limit).order_by(BusinessLeadModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count business leads by submitter."""
        result = await self.session.execute(
            select(func.count(BusinessLeadModel.id)).where(
                BusinessLeadModel.submitter_id == submitter_id
            )
        )
        return result.scalar() or 0

    async def count_by_status(self, status: BusinessLeadStatus) -> int:
        """Count business leads by status."""
        result = await self.session.execute(
            select(func.count(BusinessLeadModel.id)).where(
                BusinessLeadModel.status == str(status)
            )
        )
        return result.scalar() or 0

    def _to_entity(self, model: BusinessLeadModel) -> BusinessLead:
        """Convert model to entity."""
        return BusinessLead(
            id=model.id,
            title=model.title,
            description=model.description,
            submitter_id=model.submitter_id,
            client_name=model.client_name,
            contact_name=model.contact_name,
            contact_email=model.contact_email,
            contact_phone=model.contact_phone,
            estimated_budget=model.estimated_budget,
            expected_start_date=model.expected_start_date,
            skills_needed=model.skills_needed or [],
            location=model.location,
            status=BusinessLeadStatus(model.status),
            rejection_reason=model.rejection_reason,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
