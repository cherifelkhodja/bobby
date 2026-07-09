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

    # NEEDS-CONFIRMATION: `datetime.utcnow()` (naïf) conservé — comparé à
    # `fc.expires_at` (supposé naïf). Passer à `datetime.now(UTC)` risquerait une
    # comparaison naïf/aware.
    now = datetime.utcnow()
    soon_threshold = now + timedelta(days=30)

    async with async_session_factory() as session:
        fc_repo = FrameworkContractRepository(session)

        # Find active OR expiring-soon contracts within the 30-day window.
        # EXPIRING_SOON doit rester inclus : sans cela, un contrat déjà marqué
        # EXPIRING_SOON ne serait plus jamais re-sélectionné et ne pourrait donc
        # jamais être renouvelé (renew) ni expiré (mark_expired) à échéance —
        # un contrat expiré resterait utilisable indéfiniment.
        result = await session.execute(
            select(FrameworkContractModel).where(
                FrameworkContractModel.status.in_(
                    [
                        FrameworkContractStatus.ACTIVE.value,
                        FrameworkContractStatus.EXPIRING_SOON.value,
                    ]
                ),
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


async def archive_inactive_contract_requests():
    """CRON: Archive contract requests with no active BDC for 6 months.

    Runs daily at 3h. A contract request in ACTIVE status is archived
    when all linked purchase orders have been closed or archived for
    more than 6 months.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.contract_management.domain.value_objects.contract_request_status import (
        ContractRequestStatus,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRequestRepository,
        FrameworkContractRepository,
        PurchaseOrderRepository,
    )
    from app.contract_management.infrastructure.models import (
        ContractRequestModel,
    )
    from app.infrastructure.database.connection import async_session_factory

    # NEEDS-CONFIRMATION: `datetime.utcnow()` (naïf) conservé — comparé à
    # `cr.updated_at`/`po.updated_at` (supposés naïfs). Passer à `datetime.now(UTC)`
    # risquerait une comparaison naïf/aware.
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    async with async_session_factory() as session:
        cr_repo = ContractRequestRepository(session)
        fc_repo = FrameworkContractRepository(session)
        po_repo = PurchaseOrderRepository(session)

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

            # Find the framework contract for this CR's third party
            if not cr.third_party_id:
                continue

            fc = await fc_repo.get_active_by_third_party(cr.third_party_id)
            if not fc:
                # No FC → only archive if the CR is old (> 6 months)
                if cr.updated_at and cr.updated_at < six_months_ago:
                    cr.transition_to(ContractRequestStatus.ARCHIVED)
                    await cr_repo.save(cr)
                    archived_count += 1
                continue

            # Check if any PO is still active
            purchase_orders = await po_repo.list_by_framework_contract(fc.id)
            has_recent_active = any(
                po.status.value in ("draft", "sent", "active")
                or (po.updated_at and po.updated_at > six_months_ago)
                for po in purchase_orders
            )

            if not has_recent_active:
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
        process_framework_contract_renewals,
        "cron",
        hour=2,
        minute=0,
        id="process_framework_contract_renewals",
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
