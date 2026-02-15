"""Use case: Process document expirations (CRON job)."""

import structlog

from app.vigilance.domain.services.compliance_checker import compute_compliance_status

logger = structlog.get_logger()


class ProcessExpirationsUseCase:
    """Process document expirations and update statuses.

    Called by CRON daily. Handles:
    - VALIDATED documents expiring within 30 days → EXPIRING_SOON
    - VALIDATED / EXPIRING_SOON documents past expiry → EXPIRED
    - Recalculates compliance for affected third parties
    - Sends notifications
    """

    def __init__(
        self,
        document_repository,
        third_party_repository,
        email_service,
    ) -> None:
        self._document_repo = document_repository
        self._third_party_repo = third_party_repository
        self._email_service = email_service

    async def execute(self) -> dict:
        """Execute the expiration processing.

        Returns:
            Summary of processed documents.
        """
        expired_count = 0
        expiring_soon_count = 0
        affected_third_parties: set = set()

        # Process expired documents
        expired_docs = await self._document_repo.list_expired()
        for doc in expired_docs:
            doc.mark_expired()
            await self._document_repo.save(doc)
            expired_count += 1
            affected_third_parties.add(doc.third_party_id)

            third_party = await self._third_party_repo.get_by_id(doc.third_party_id)
            if third_party:
                await self._email_service.send_document_expired(
                    to=third_party.contact_email,
                    third_party_name=third_party.company_name,
                    doc_type=doc.document_type.display_name,
                )

        # Process expiring soon documents (30 days)
        expiring_docs = await self._document_repo.list_expiring(days_ahead=30)
        for doc in expiring_docs:
            if doc.status.value == "validated":
                doc.mark_expiring_soon()
                await self._document_repo.save(doc)
                expiring_soon_count += 1
                affected_third_parties.add(doc.third_party_id)

                third_party = await self._third_party_repo.get_by_id(doc.third_party_id)
                if third_party and doc.expires_at:
                    from datetime import datetime

                    days_left = (doc.expires_at - datetime.utcnow()).days
                    await self._email_service.send_document_expiring(
                        to=third_party.contact_email,
                        third_party_name=third_party.company_name,
                        doc_type=doc.document_type.display_name,
                        days_left=max(days_left, 0),
                    )

        # Recalculate compliance for affected third parties
        for tp_id in affected_third_parties:
            third_party = await self._third_party_repo.get_by_id(tp_id)
            if third_party:
                all_docs = await self._document_repo.list_by_third_party(tp_id)
                new_status = compute_compliance_status(third_party.type, all_docs)
                if third_party.compliance_status != new_status:
                    third_party.update_compliance_status(new_status)
                    await self._third_party_repo.save(third_party)

        summary = {
            "expired": expired_count,
            "expiring_soon": expiring_soon_count,
            "affected_third_parties": len(affected_third_parties),
        }

        logger.info("expirations_processed", **summary)
        return summary
