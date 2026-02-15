"""Use case: Request documents for a third party based on requirements."""

from uuid import UUID

import structlog

from app.third_party.domain.exceptions import ThirdPartyNotFoundError
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS

logger = structlog.get_logger()


class RequestDocumentsUseCase:
    """Create REQUESTED documents for a third party based on its type.

    Looks up the vigilance requirements for the third party type and creates
    a VigilanceDocument for each required document type that is not already
    active (REQUESTED, RECEIVED, or VALIDATED).
    """

    def __init__(self, third_party_repository, document_repository) -> None:
        self._third_party_repo = third_party_repository
        self._document_repo = document_repository

    async def execute(self, third_party_id: UUID) -> list[VigilanceDocument]:
        """Execute the use case.

        Args:
            third_party_id: ID of the third party.

        Returns:
            List of newly created document requests.

        Raises:
            ThirdPartyNotFoundError: If the third party does not exist.
        """
        third_party = await self._third_party_repo.get_by_id(third_party_id)
        if not third_party:
            raise ThirdPartyNotFoundError(str(third_party_id))

        requirements = VIGILANCE_REQUIREMENTS.get(third_party.type, [])
        if not requirements:
            logger.info(
                "no_vigilance_requirements",
                third_party_id=str(third_party_id),
                type=third_party.type.value,
            )
            return []

        existing_docs = await self._document_repo.list_by_third_party(third_party_id)
        # Set of doc types that already have an active document
        active_types = {
            doc.document_type.value
            for doc in existing_docs
            if doc.status.value in ("requested", "received", "validated", "expiring_soon")
        }

        created = []
        for req in requirements:
            doc_type = req["type"]
            if doc_type.value in active_types:
                continue

            document = VigilanceDocument(
                third_party_id=third_party_id,
                document_type=doc_type,
            )
            saved = await self._document_repo.save(document)
            created.append(saved)

        if created:
            logger.info(
                "documents_requested",
                third_party_id=str(third_party_id),
                count=len(created),
                types=[d.document_type.value for d in created],
            )

        return created
