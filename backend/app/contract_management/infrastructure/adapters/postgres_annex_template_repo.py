"""Repository for contract annex templates."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.infrastructure.models import ContractAnnexTemplateModel


@dataclass
class AnnexTemplate:
    """Annex template data object."""

    id: UUID
    annexe_key: str
    annexe_number: int
    title: str
    content: str
    is_conditional: bool
    condition_field: str | None
    is_active: bool
    updated_at: datetime
    updated_by: UUID | None = None


class AnnexTemplateRepository:
    """Repository for reading and updating contract annex templates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[AnnexTemplate]:
        """Return all annexes ordered by annexe_number."""
        result = await self._db.execute(
            select(ContractAnnexTemplateModel).order_by(
                ContractAnnexTemplateModel.annexe_number
            )
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_active(self) -> list[AnnexTemplate]:
        """Return active annexes ordered by annexe_number."""
        result = await self._db.execute(
            select(ContractAnnexTemplateModel)
            .where(ContractAnnexTemplateModel.is_active.is_(True))
            .order_by(ContractAnnexTemplateModel.annexe_number)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_by_key(self, annexe_key: str) -> AnnexTemplate | None:
        """Return an annexe by its key."""
        result = await self._db.execute(
            select(ContractAnnexTemplateModel).where(
                ContractAnnexTemplateModel.annexe_key == annexe_key
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def reorder(self, ordered_keys: list[str]) -> None:
        """Update annexe_number for each key based on the provided order."""
        result = await self._db.execute(select(ContractAnnexTemplateModel))
        models_by_key = {m.annexe_key: m for m in result.scalars().all()}
        for idx, key in enumerate(ordered_keys, start=1):
            if key in models_by_key:
                models_by_key[key].annexe_number = idx
        await self._db.flush()

    async def delete(self, annexe_key: str) -> bool:
        """Delete an annexe template. Returns True if deleted, False if not found."""
        from sqlalchemy import delete as _delete
        result = await self._db.execute(
            _delete(ContractAnnexTemplateModel).where(
                ContractAnnexTemplateModel.annexe_key == annexe_key
            )
        )
        await self._db.flush()
        return result.rowcount > 0

    async def update(
        self,
        annexe_key: str,
        *,
        content: str | None = None,
        title: str | None = None,
        is_active: bool | None = None,
        updated_by: UUID | None = None,
    ) -> AnnexTemplate | None:
        """Update an annexe template. Returns the updated annexe or None if not found."""
        result = await self._db.execute(
            select(ContractAnnexTemplateModel).where(
                ContractAnnexTemplateModel.annexe_key == annexe_key
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        if content is not None:
            model.content = content
        if title is not None:
            model.title = title
        if is_active is not None:
            model.is_active = is_active
        if updated_by is not None:
            model.updated_by = updated_by
        model.updated_at = datetime.utcnow()

        await self._db.flush()
        return self._to_domain(model)

    def _to_domain(self, model: ContractAnnexTemplateModel) -> AnnexTemplate:
        return AnnexTemplate(
            id=model.id,
            annexe_key=model.annexe_key,
            annexe_number=model.annexe_number,
            title=model.title,
            content=model.content,
            is_conditional=model.is_conditional,
            condition_field=model.condition_field,
            is_active=model.is_active,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
