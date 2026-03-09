"""Repository for contract article templates."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.infrastructure.models import ContractArticleTemplateModel


@dataclass
class ArticleTemplate:
    """Article template data object."""

    id: UUID
    article_key: str
    article_number: int
    title: str
    content: str
    is_editable: bool
    is_active: bool
    updated_at: datetime
    updated_by: UUID | None = None


class ArticleTemplateRepository:
    """Repository for reading and updating contract article templates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[ArticleTemplate]:
        """Return all articles ordered by article_number."""
        result = await self._db.execute(
            select(ContractArticleTemplateModel).order_by(
                ContractArticleTemplateModel.article_number
            )
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_active(self) -> list[ArticleTemplate]:
        """Return active articles ordered by article_number."""
        result = await self._db.execute(
            select(ContractArticleTemplateModel)
            .where(ContractArticleTemplateModel.is_active.is_(True))
            .order_by(ContractArticleTemplateModel.article_number)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_by_key(self, article_key: str) -> ArticleTemplate | None:
        """Return an article by its key."""
        result = await self._db.execute(
            select(ContractArticleTemplateModel).where(
                ContractArticleTemplateModel.article_key == article_key
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def reorder(self, ordered_keys: list[str]) -> None:
        """Update article_number for each key based on the provided order."""
        result = await self._db.execute(select(ContractArticleTemplateModel))
        models_by_key = {m.article_key: m for m in result.scalars().all()}
        for idx, key in enumerate(ordered_keys, start=1):
            if key in models_by_key:
                models_by_key[key].article_number = idx
        await self._db.flush()

    async def delete(self, article_key: str) -> bool:
        """Delete an article template. Returns True if deleted, False if not found."""
        from sqlalchemy import delete as _delete
        result = await self._db.execute(
            _delete(ContractArticleTemplateModel).where(
                ContractArticleTemplateModel.article_key == article_key
            )
        )
        await self._db.flush()
        return result.rowcount > 0

    async def update(
        self,
        article_key: str,
        *,
        content: str | None = None,
        title: str | None = None,
        is_editable: bool | None = None,
        is_active: bool | None = None,
        updated_by: UUID | None = None,
    ) -> ArticleTemplate | None:
        """Update an article template. Returns the updated article or None if not found."""
        result = await self._db.execute(
            select(ContractArticleTemplateModel).where(
                ContractArticleTemplateModel.article_key == article_key
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        if content is not None:
            model.content = content
        if title is not None:
            model.title = title
        if is_editable is not None:
            model.is_editable = is_editable
        if is_active is not None:
            model.is_active = is_active
        if updated_by is not None:
            model.updated_by = updated_by
        model.updated_at = datetime.utcnow()

        await self._db.flush()
        return self._to_domain(model)

    def _to_domain(self, model: ContractArticleTemplateModel) -> ArticleTemplate:
        return ArticleTemplate(
            id=model.id,
            article_key=model.article_key,
            article_number=model.article_number,
            title=model.title,
            content=model.content,
            is_editable=model.is_editable,
            is_active=model.is_active,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
