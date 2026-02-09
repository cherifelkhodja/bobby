"""Database connection management."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Log the database URL being used (masked for security)
db_url = settings.async_database_url
masked_url = (
    db_url.split("@")[0].rsplit(":", 1)[0] + ":***@" + db_url.split("@")[-1]
    if "@" in db_url
    else db_url
)
logger.info(f"Creating async engine with URL: {masked_url}")

engine = create_async_engine(
    db_url,
    echo=settings.is_development,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
