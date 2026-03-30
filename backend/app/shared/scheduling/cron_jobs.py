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


async def process_framework_contract_renewals():
    """CRON: Process framework contract expirations and tacit renewals.

    Runs daily at 2h.
    - Contracts expiring within 30 days → status EXPIRING_SOON
    - Expired contracts with tacit_renewal=True → extend by 1 year
    - Expired contracts without tacit_renewal → status EXPIRED
    """
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.contract_management.domain.value_objects.framework_contract_status import (
        FrameworkContractStatus,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        FrameworkContractRepository,
    )
    from app.contract_management.infrastructure.models import FrameworkContractModel
    from app.infrastructure.database.connection import async_session_factory

    now = datetime.utcnow()
    soon_threshold = now + timedelta(days=30)

    async with async_session_factory() as session:
        fc_repo = FrameworkContractRepository(session)

        # Find active contracts expiring within 30 days
        result = await session.execute(
            select(FrameworkContractModel).where(
                FrameworkContractModel.status == FrameworkContractStatus.ACTIVE.value,
                FrameworkContractModel.expires_at.isnot(None),
                FrameworkContractModel.expires_at <= soon_threshold,
            )
        )
        expiring_models = result.scalars().all()

        renewed = 0
        expired = 0
        warned = 0

        for model in expiring_models:
            fc = fc_repo._to_entity(model)

            if fc.expires_at and fc.expires_at <= now:
                # Contract has expired
                if fc.tacit_renewal:
                    # Tacit renewal: extend by 1 year
                    fc.renew(new_expires_at=fc.expires_at + timedelta(days=365))
                    await fc_repo.save(fc)
                    renewed += 1
                else:
                    fc.mark_expired()
                    await fc_repo.save(fc)
                    expired += 1
            else:
                # Contract expiring soon — mark as warning
                fc.mark_expiring_soon()
                await fc_repo.save(fc)
                warned += 1

        await session.commit()
        logger.info(
            "cron_framework_contract_renewals_completed",
            renewed=renewed,
            expired=expired,
            warned=warned,
        )


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

    scheduler.add_job(
        process_framework_contract_renewals,
        "cron",
        hour=2,
        minute=0,
        id="process_framework_contract_renewals",
        replace_existing=True,
    )

    logger.info("scheduler_configured", jobs=len(scheduler.get_jobs()))
    return scheduler
