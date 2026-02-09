"""CV Template repository implementation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import CvTemplate
from app.infrastructure.database.models import CvTemplateModel


class CvTemplateRepository:
    """CV Template repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, template_id: UUID) -> CvTemplate | None:
        """Get template by ID."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> CvTemplate | None:
        """Get template by unique name."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, template: CvTemplate) -> CvTemplate:
        """Save template (create or update)."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.name = template.name
            model.display_name = template.display_name
            model.description = template.description
            model.file_content = template.file_content
            model.file_name = template.file_name
            model.is_active = template.is_active
            model.updated_at = datetime.utcnow()
        else:
            model = CvTemplateModel(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                file_content=template.file_content,
                file_name=template.file_name,
                is_active=template.is_active,
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, template_id: UUID) -> bool:
        """Delete template by ID."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_active(self) -> list[CvTemplate]:
        """List all active templates."""
        result = await self.session.execute(
            select(CvTemplateModel)
            .where(CvTemplateModel.is_active == True)
            .order_by(CvTemplateModel.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(self) -> list[CvTemplate]:
        """List all templates (including inactive)."""
        result = await self.session.execute(select(CvTemplateModel).order_by(CvTemplateModel.name))
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: CvTemplateModel) -> CvTemplate:
        """Convert model to entity."""
        return CvTemplate(
            id=model.id,
            name=model.name,
            display_name=model.display_name,
            description=model.description,
            file_content=model.file_content,
            file_name=model.file_name,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
