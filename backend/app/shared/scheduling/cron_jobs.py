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

        async def _resolve_company_email_for_tp(third_party_id):
            """Resolve company email_from from a third_party_id via its most recent CR."""
            from sqlalchemy import select

            from app.contract_management.infrastructure.models import (
                ContractCompanyModel,
                ContractRequestModel,
            )

            cr_result = await session.execute(
                select(ContractRequestModel.company_id)
                .where(ContractRequestModel.third_party_id == third_party_id)
                .order_by(ContractRequestModel.created_at.desc())
                .limit(1)
            )
            company_id = cr_result.scalar_one_or_none()
            if not company_id:
                return None, None
            c_result = await session.execute(
                select(ContractCompanyModel.email_from, ContractCompanyModel.name).where(
                    ContractCompanyModel.id == company_id
                )
            )
            row = c_result.first()
            return (row.email_from, row.name) if row else (None, None)

        use_case = ProcessExpirationsUseCase(
            document_repository=DocumentRepository(session),
            third_party_repository=ThirdPartyRepository(session),
            email_service=EmailService(settings),
            send_alerts=settings.FEATURE_DOCUMENT_EXPIRATION_ALERTS,
            company_email_resolver=_resolve_company_email_for_tp,
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


async def archive_inactive_contract_requests():
    """CRON: Archive contract requests inactive for 6 months.

    Runs daily at 3h. A contract request in ACTIVE status is archived
    when it has not been updated for more than 6 months.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.contract_management.domain.value_objects.contract_request_status import (
        ContractRequestStatus,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRequestRepository,
    )
    from app.contract_management.infrastructure.models import (
        ContractRequestModel,
    )
    from app.infrastructure.database.connection import async_session_factory

    # NEEDS-CONFIRMATION: `datetime.utcnow()` (naïf) conservé — comparé à
    # `cr.updated_at` (supposé naïf). Passer à `datetime.now(UTC)`
    # risquerait une comparaison naïf/aware.
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    async with async_session_factory() as session:
        cr_repo = ContractRequestRepository(session)

        # Find all ACTIVE contract requests
        result = await session.execute(
            select(ContractRequestModel).where(
                ContractRequestModel.status == ContractRequestStatus.ACTIVE.value,
            )
        )
        active_crs = result.scalars().all()

        archived_count = 0
        for cr_model in active_crs:
            cr = cr_repo._to_entity(cr_model)

            # Archive if the CR has been inactive for more than 6 months.
            if cr.updated_at and cr.updated_at < six_months_ago:
                cr.transition_to(ContractRequestStatus.ARCHIVED)
                await cr_repo.save(cr)
                archived_count += 1

        await session.commit()
        logger.info(
            "cron_archive_inactive_contracts_completed",
            archived=archived_count,
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
        archive_inactive_contract_requests,
        "cron",
        hour=3,
        minute=0,
        id="archive_inactive_contract_requests",
        replace_existing=True,
    )

    logger.info("scheduler_configured", jobs=len(scheduler.get_jobs()))
    return scheduler
