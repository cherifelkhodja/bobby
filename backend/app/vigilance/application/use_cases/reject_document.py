"""Use case: Reject a vigilance document."""

from uuid import UUID

import structlog

from app.vigilance.domain.exceptions import DocumentNotFoundError
from app.vigilance.domain.services.compliance_checker import compute_compliance_status

logger = structlog.get_logger()


class RejectDocumentUseCase:
    """Reject a document and notify the third party.

    Transitions the document to REJECTED, sends notification email,
    and creates a new REQUESTED document for the same type.
    """

    def __init__(
        self,
        document_repository,
        third_party_repository,
        email_service,
        portal_base_url: str,
    ) -> None:
        self._document_repo = document_repository
        self._third_party_repo = third_party_repository
        self._email_service = email_service
        self._portal_base_url = portal_base_url

    async def execute(
        self,
        document_id: UUID,
        reason: str,
    ):
        """Execute the use case.

        Args:
            document_id: ID of the document to reject.
            reason: Rejection reason.

        Returns:
            The updated document entity.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        document = await self._document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(str(document_id))

        third_party = await self._third_party_repo.get_by_id(document.third_party_id)
        if not third_party:
            raise DocumentNotFoundError(str(document_id))

        document.reject(reason=reason)
        saved = await self._document_repo.save(document)

        # Recalculate compliance
        all_docs = await self._document_repo.list_by_third_party(document.third_party_id)
        new_status = compute_compliance_status(third_party.type, all_docs)
        if third_party.compliance_status != new_status:
            third_party.update_compliance_status(new_status)
            await self._third_party_repo.save(third_party)

        # Send rejection notification
        await self._email_service.send_document_rejected(
            to=third_party.contact_email,
            third_party_name=third_party.company_name,
            doc_type=document.document_type.display_name,
            reason=reason,
            portal_link=self._portal_base_url,
        )

        logger.info(
            "document_rejected",
            document_id=str(saved.id),
            third_party_id=str(third_party.id),
            reason=reason,
        )
        return saved
