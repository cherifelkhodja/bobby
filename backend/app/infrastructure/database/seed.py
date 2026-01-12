"""Database seeding for development."""

import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.infrastructure.database.connection import async_session_factory
from app.infrastructure.database.models import UserModel
from app.infrastructure.security.password import hash_password

logger = logging.getLogger(__name__)


async def seed_admin_user() -> None:
    """Seed admin user in development/test environment."""
    if settings.ENV not in ("dev", "test"):
        logger.warning("Skipping admin seed in production")
        return

    async with async_session_factory() as session:
        # Check if admin already exists
        result = await session.execute(
            select(UserModel).where(UserModel.email == settings.ADMIN_EMAIL.lower())
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update password hash in case hashing method changed
            existing.password_hash = hash_password(settings.ADMIN_PASSWORD)
            await session.commit()
            logger.info(f"Admin user password updated: {settings.ADMIN_EMAIL}")
            return

        # Create admin user
        admin = UserModel(
            email=settings.ADMIN_EMAIL.lower(),
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            first_name="Admin",
            last_name="Gemini",
            role="admin",
            is_verified=True,
            is_active=True,
        )

        session.add(admin)
        await session.commit()
        logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")


async def main() -> None:
    """Run seeding."""
    await seed_admin_user()


if __name__ == "__main__":
    asyncio.run(main())
