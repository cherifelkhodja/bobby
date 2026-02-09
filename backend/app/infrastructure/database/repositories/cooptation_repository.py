"""Cooptation repository implementation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Candidate, Cooptation, Opportunity
from app.domain.value_objects import CooptationStatus, Email, Phone
from app.infrastructure.database.models import CandidateModel, CooptationModel


class CooptationRepository:
    """Cooptation repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, cooptation_id: UUID) -> Cooptation | None:
        """Get cooptation by ID with related entities."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.id == cooptation_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_candidate_email_and_opportunity(
        self,
        email: str,
        opportunity_id: UUID,
    ) -> Cooptation | None:
        """Check if candidate already proposed for opportunity."""
        result = await self.session.execute(
            select(CooptationModel)
            .join(CandidateModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(
                CandidateModel.email == email.lower(),
                CooptationModel.opportunity_id == opportunity_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, cooptation: Cooptation) -> Cooptation:
        """Save cooptation (create or update)."""
        result = await self.session.execute(
            select(CooptationModel).where(CooptationModel.id == cooptation.id)
        )
        model = result.scalar_one_or_none()

        # Convert status history to JSON-serializable format
        status_history = [
            {
                "from_status": str(sh.from_status),
                "to_status": str(sh.to_status),
                "changed_at": sh.changed_at.isoformat(),
                "changed_by": str(sh.changed_by) if sh.changed_by else None,
                "comment": sh.comment,
            }
            for sh in cooptation.status_history
        ]

        if model:
            model.candidate_id = cooptation.candidate.id
            model.opportunity_id = cooptation.opportunity.id
            model.submitter_id = cooptation.submitter_id
            model.status = str(cooptation.status)
            model.external_positioning_id = cooptation.external_positioning_id
            model.status_history = status_history
            model.rejection_reason = cooptation.rejection_reason
            model.updated_at = datetime.utcnow()
        else:
            model = CooptationModel(
                id=cooptation.id,
                candidate_id=cooptation.candidate.id,
                opportunity_id=cooptation.opportunity.id,
                submitter_id=cooptation.submitter_id,
                status=str(cooptation.status),
                external_positioning_id=cooptation.external_positioning_id,
                status_history=status_history,
                rejection_reason=cooptation.rejection_reason,
                submitted_at=cooptation.submitted_at,
                updated_at=cooptation.updated_at,
            )
            self.session.add(model)

        await self.session.flush()

        # Reload with relationships
        return await self.get_by_id(cooptation.id)  # type: ignore

    async def delete(self, cooptation_id: UUID) -> bool:
        """Delete cooptation by ID."""
        result = await self.session.execute(
            select(CooptationModel).where(CooptationModel.id == cooptation_id)
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
    ) -> list[Cooptation]:
        """List cooptations by submitter."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.submitter_id == submitter_id)
            .offset(skip)
            .limit(limit)
            .order_by(CooptationModel.submitted_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_status(
        self,
        status: CooptationStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cooptation]:
        """List cooptations by status."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.status == str(status))
            .offset(skip)
            .limit(limit)
            .order_by(CooptationModel.submitted_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: CooptationStatus | None = None,
    ) -> list[Cooptation]:
        """List all cooptations with optional status filter."""
        query = select(CooptationModel).options(
            selectinload(CooptationModel.candidate),
            selectinload(CooptationModel.opportunity),
        )

        if status:
            query = query.where(CooptationModel.status == str(status))

        query = query.offset(skip).limit(limit).order_by(CooptationModel.submitted_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count cooptations by submitter."""
        result = await self.session.execute(
            select(func.count(CooptationModel.id)).where(
                CooptationModel.submitter_id == submitter_id
            )
        )
        return result.scalar() or 0

    async def count_by_status(self, status: CooptationStatus) -> int:
        """Count cooptations by status."""
        result = await self.session.execute(
            select(func.count(CooptationModel.id)).where(CooptationModel.status == str(status))
        )
        return result.scalar() or 0

    async def get_stats_by_submitter(self, submitter_id: UUID) -> dict[str, int]:
        """Get cooptation statistics for a submitter."""
        stats = {"total": 0, "pending": 0, "in_review": 0, "accepted": 0, "rejected": 0}

        for status in CooptationStatus:
            result = await self.session.execute(
                select(func.count(CooptationModel.id)).where(
                    CooptationModel.submitter_id == submitter_id,
                    CooptationModel.status == str(status),
                )
            )
            count = result.scalar() or 0
            stats[str(status)] = count
            stats["total"] += count

        return stats

    def _to_entity(self, model: CooptationModel) -> Cooptation:
        """Convert model to entity."""
        from app.domain.entities.cooptation import StatusChange

        # Convert candidate
        candidate = Candidate(
            id=model.candidate.id,
            email=Email(model.candidate.email),
            first_name=model.candidate.first_name,
            last_name=model.candidate.last_name,
            civility=model.candidate.civility,
            phone=Phone(model.candidate.phone) if model.candidate.phone else None,
            cv_filename=model.candidate.cv_filename,
            cv_path=model.candidate.cv_path,
            daily_rate=model.candidate.daily_rate,
            note=model.candidate.note,
            external_id=model.candidate.external_id,
            created_at=model.candidate.created_at,
            updated_at=model.candidate.updated_at,
        )

        # Convert opportunity
        opportunity = Opportunity(
            id=model.opportunity.id,
            external_id=model.opportunity.external_id,
            title=model.opportunity.title,
            reference=model.opportunity.reference,
            start_date=model.opportunity.start_date,
            end_date=model.opportunity.end_date,
            response_deadline=model.opportunity.response_deadline,
            budget=model.opportunity.budget,
            manager_name=model.opportunity.manager_name,
            manager_email=model.opportunity.manager_email,
            manager_boond_id=model.opportunity.manager_boond_id,
            client_name=model.opportunity.client_name,
            description=model.opportunity.description,
            skills=model.opportunity.skills or [],
            location=model.opportunity.location,
            is_active=model.opportunity.is_active,
            is_shared=model.opportunity.is_shared,
            owner_id=model.opportunity.owner_id,
            synced_at=model.opportunity.synced_at,
            created_at=model.opportunity.created_at,
            updated_at=model.opportunity.updated_at,
        )

        # Convert status history
        status_history = []
        for sh in model.status_history or []:
            status_history.append(
                StatusChange(
                    from_status=CooptationStatus(sh["from_status"]),
                    to_status=CooptationStatus(sh["to_status"]),
                    changed_at=datetime.fromisoformat(sh["changed_at"]),
                    changed_by=UUID(sh["changed_by"]) if sh.get("changed_by") else None,
                    comment=sh.get("comment"),
                )
            )

        return Cooptation(
            id=model.id,
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=model.submitter_id,
            status=CooptationStatus(model.status),
            external_positioning_id=model.external_positioning_id,
            status_history=status_history,
            rejection_reason=model.rejection_reason,
            submitted_at=model.submitted_at,
            updated_at=model.updated_at,
        )
