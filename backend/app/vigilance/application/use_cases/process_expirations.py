"""Use case: Process document expirations (CRON job)."""

from collections import defaultdict
from datetime import datetime, timedelta

import structlog

from app.vigilance.domain.services.compliance_checker import compute_compliance_status

logger = structlog.get_logger()

# Cooldown: don't re-send alerts if already sent within this period
ALERT_COOLDOWN_DAYS = 7


class ProcessExpirationsUseCase:
    """Process document expirations and update statuses.

    Called by CRON daily. Handles:
    - VALIDATED documents expiring within 30 days → EXPIRING_SOON
    - VALIDATED / EXPIRING_SOON documents past expiry → EXPIRED
    - Recalculates compliance for affected third parties
    - Sends grouped notifications (one email per third party, not per document)
    - Respects cooldown: no re-alert within 7 days for same third party
    """

    def __init__(
        self,
        document_repository,
        third_party_repository,
        email_service,
        send_alerts: bool = True,
        company_email_resolver=None,
    ) -> None:
        self._document_repo = document_repository
        self._third_party_repo = third_party_repository
        self._email_service = email_service
        self._send_alerts = send_alerts
        self._company_email_resolver = company_email_resolver

    async def execute(self) -> dict:
        """Execute the expiration processing.

        Returns:
            Summary of processed documents.
        """
        expired_count = 0
        expiring_soon_count = 0
        affected_third_parties: set = set()

        # Group alerts by third_party_id
        expired_by_tp: dict[str, list[str]] = defaultdict(list)
        expiring_by_tp: dict[str, list[tuple[str, int]]] = defaultdict(list)

        # Process expired documents
        expired_docs = await self._document_repo.list_expired()
        for doc in expired_docs:
            doc.mark_expired()
            await self._document_repo.save(doc)
            expired_count += 1
            affected_third_parties.add(doc.third_party_id)
            expired_by_tp[doc.third_party_id].append(doc.document_type.display_name)

        # Process expiring soon documents (30 days)
        expiring_docs = await self._document_repo.list_expiring(days_ahead=30)
        for doc in expiring_docs:
            if doc.status.value == "validated":
                doc.mark_expiring_soon()
                await self._document_repo.save(doc)
                expiring_soon_count += 1
                affected_third_parties.add(doc.third_party_id)
                if doc.expires_at:
                    days_left = max((doc.expires_at - datetime.utcnow()).days, 0)
                    expiring_by_tp[doc.third_party_id].append(
                        (doc.document_type.display_name, days_left)
                    )

        # Send grouped alerts per third party (with cooldown)
        emails_sent = 0
        if self._send_alerts:
            all_tp_ids = set(expired_by_tp.keys()) | set(expiring_by_tp.keys())
            for tp_id in all_tp_ids:
                third_party = await self._third_party_repo.get_by_id(tp_id)
                if not third_party or not third_party.contact_email:
                    continue

                # Cooldown check: skip if alert was sent recently
                if self._was_recently_alerted(third_party):
                    logger.info(
                        "expiration_alert_cooldown",
                        third_party_id=str(tp_id),
                        company=third_party.company_name,
                    )
                    continue

                expired_docs_list = expired_by_tp.get(tp_id, [])
                expiring_docs_list = expiring_by_tp.get(tp_id, [])

                try:
                    _from_email, _company_name = None, None
                    if self._company_email_resolver:
                        try:
                            _from_email, _company_name = await self._company_email_resolver(tp_id)
                        except Exception:
                            pass
                    await self._email_service.send_document_expiration_summary(
                        to=third_party.contact_email,
                        third_party_name=third_party.company_name or "Fournisseur",
                        expired_docs=expired_docs_list,
                        expiring_docs=expiring_docs_list,
                        from_email=_from_email,
                        company_name=_company_name,
                    )
                    emails_sent += 1

                    # Mark alert timestamp on third party for cooldown
                    third_party.last_expiration_alert_at = datetime.utcnow()
                    await self._third_party_repo.save(third_party)
                except Exception as exc:
                    logger.warning(
                        "expiration_alert_email_failed",
                        third_party_id=str(tp_id),
                        error=str(exc),
                    )

        # Recalculate compliance for affected third parties
        for tp_id in affected_third_parties:
            third_party = await self._third_party_repo.get_by_id(tp_id)
            if third_party:
                all_docs = await self._document_repo.list_by_third_party(tp_id)
                new_status = compute_compliance_status(all_docs)
                if third_party.compliance_status != new_status:
                    third_party.update_compliance_status(new_status)
                    await self._third_party_repo.save(third_party)

        summary = {
            "expired": expired_count,
            "expiring_soon": expiring_soon_count,
            "affected_third_parties": len(affected_third_parties),
            "emails_sent": emails_sent,
        }

        logger.info("expirations_processed", **summary)
        return summary

    @staticmethod
    def _was_recently_alerted(third_party) -> bool:
        """Check if the third party was alerted within the cooldown period."""
        last_alert = getattr(third_party, "last_expiration_alert_at", None)
        if not last_alert:
            return False
        return (datetime.utcnow() - last_alert) < timedelta(days=ALERT_COOLDOWN_DAYS)
