"""Candidate repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Candidate
from app.domain.value_objects import Email, Phone
from app.infrastructure.database.models import CandidateModel


class CandidateRepository:
    """Candidate repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, candidate_id: UUID) -> Optional[Candidate]:
        """Get candidate by ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[Candidate]:
        """Get candidate by email."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_external_id(self, external_id: str) -> Optional[Candidate]:
        """Get candidate by external BoondManager ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.external_id == external_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, candidate: Candidate) -> Candidate:
        """Save candidate (create or update)."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.email = str(candidate.email).lower()
            model.first_name = candidate.first_name
            model.last_name = candidate.last_name
            model.civility = candidate.civility
            model.phone = str(candidate.phone) if candidate.phone else None
            model.cv_filename = candidate.cv_filename
            model.cv_path = candidate.cv_path
            model.daily_rate = candidate.daily_rate
            model.note = candidate.note
            model.external_id = candidate.external_id
            model.updated_at = datetime.utcnow()
        else:
            model = CandidateModel(
                id=candidate.id,
                email=str(candidate.email).lower(),
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                civility=candidate.civility,
                phone=str(candidate.phone) if candidate.phone else None,
                cv_filename=candidate.cv_filename,
                cv_path=candidate.cv_path,
                daily_rate=candidate.daily_rate,
                note=candidate.note,
                external_id=candidate.external_id,
                created_at=candidate.created_at,
                updated_at=candidate.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, candidate_id: UUID) -> bool:
        """Delete candidate by ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    def _to_entity(self, model: CandidateModel) -> Candidate:
        """Convert model to entity."""
        return Candidate(
            id=model.id,
            email=Email(model.email),
            first_name=model.first_name,
            last_name=model.last_name,
            civility=model.civility,
            phone=Phone(model.phone) if model.phone else None,
            cv_filename=model.cv_filename,
            cv_path=model.cv_path,
            daily_rate=model.daily_rate,
            note=model.note,
            external_id=model.external_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
