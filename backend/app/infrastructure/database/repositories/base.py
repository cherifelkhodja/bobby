"""Base repository with common functionality."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Type variables for generic repository
TEntity = TypeVar("TEntity")
TModel = TypeVar("TModel")


class BaseRepository(ABC, Generic[TEntity, TModel]):
    """Abstract base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    @abstractmethod
    def model_class(self) -> type:
        """Return the SQLAlchemy model class."""
        pass

    @abstractmethod
    def _to_entity(self, model: TModel) -> TEntity:
        """Convert model to domain entity."""
        pass

    @abstractmethod
    def _to_model(self, entity: TEntity) -> TModel:
        """Convert domain entity to model."""
        pass

    async def get_by_id(self, entity_id: UUID) -> TEntity | None:
        """Get entity by ID."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def count(self) -> int:
        """Count total entities."""
        result = await self.session.execute(select(func.count(self.model_class.id)))
        return result.scalar() or 0

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        result = await self.session.execute(
            select(func.count(self.model_class.id)).where(self.model_class.id == entity_id)
        )
        return (result.scalar() or 0) > 0
