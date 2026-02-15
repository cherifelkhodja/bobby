"""APScheduler CRON job configuration.

Manages recurring background tasks for the application:
- Document expiration monitoring
- Collection reminders
- RGPD purge
- Magic link cleanup
"""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = structlog.get_logger()

scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def check_document_expirations():
    """CRON: Check and process document expirations.

    Runs daily at 8h. Transitions VALIDATED → EXPIRING_SOON (J-30)
    and EXPIRING_SOON → EXPIRED (J0). Sends notifications.
    """
    from app.config import get_settings
    from app.infrastructure.database.connection import async_session_factory
    from app.infrastructure.email.sender import EmailService
    from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
        ThirdPartyRepository,
    )
    from app.vigilance.application.use_cases.process_expirations import (
        ProcessExpirationsUseCase,
    )
    from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository

    settings = get_settings()
    async with async_session_factory() as session:
        use_case = ProcessExpirationsUseCase(
            document_repository=DocumentRepository(session),
            third_party_repository=ThirdPartyRepository(session),
            email_service=EmailService(settings),
        )
        result = await use_case.execute()
        await session.commit()
        logger.info("cron_document_expirations_completed", **result)


async def revoke_expired_magic_links():
    """CRON: Revoke expired magic links.

    Runs daily at midnight. Cleans up expired links.
    """
    from app.infrastructure.database.connection import async_session_factory
    from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
        MagicLinkRepository,
    )

    async with async_session_factory() as session:
        repo = MagicLinkRepository(session)
        revoked = await repo.revoke_expired()
        await session.commit()
        logger.info("cron_magic_links_revoked", count=revoked)


def setup_scheduler():
    """Configure and return the APScheduler instance.

    Call this during application startup.
    """
    scheduler.add_job(
        check_document_expirations,
        "cron",
        hour=8,
        minute=0,
        id="check_document_expirations",
        replace_existing=True,
    )

    scheduler.add_job(
        revoke_expired_magic_links,
        "cron",
        hour=0,
        minute=0,
        id="revoke_expired_magic_links",
        replace_existing=True,
    )

    logger.info("scheduler_configured", jobs=len(scheduler.get_jobs()))
    return scheduler
