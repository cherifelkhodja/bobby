"""FastAPI dependency injection."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.database.connection import get_async_session
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.service_factory import ServiceFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_async_session():
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client dependency."""
    async for client in get_redis_client():
        yield client


def get_boond_client(settings: Annotated[Settings, Depends(get_settings)]) -> BoondClient:
    """Get BoondManager client dependency."""
    return BoondClient(settings)


def get_service_factory(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ServiceFactory:
    """Get ServiceFactory dependency.

    Usage in routes:
        @router.post("")
        async def create_cooptation(
            request: CreateCooptationRequest,
            services: Services,
        ):
            use_case = services.create_cooptation_use_case()
            return await use_case.execute(command)
    """
    return ServiceFactory(db=db, settings=settings)


# Type aliases for dependencies
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Boond = Annotated[BoondClient, Depends(get_boond_client)]
Services = Annotated[ServiceFactory, Depends(get_service_factory)]
