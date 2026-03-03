"""Use case: Request documents for a third party based on requirements."""

from uuid import UUID

import structlog

from app.third_party.domain.exceptions import ThirdPartyNotFoundError
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.services.vigilance_requirements import REQUIREMENTS_BY_ENTITY_CATEGORY

logger = structlog.get_logger()


class RequestDocumentsUseCase:
    """Create REQUESTED documents for a third party based on entity category.

    The entity_category ("ei" or "societe") must be passed explicitly since it
    cannot be inferred from third_party_type alone (a freelance may be either).

    Idempotent: skips document types that already have an active document
    (REQUESTED, RECEIVED, VALIDATED, EXPIRING_SOON).
    """

    def __init__(self, third_party_repository, document_repository) -> None:
        self._third_party_repo = third_party_repository
        self._document_repo = document_repository

    async def execute(
        self,
        third_party_id: UUID,
        entity_category: str,
    ) -> list[VigilanceDocument]:
        """Execute the use case.

        Args:
            third_party_id: ID of the third party.
            entity_category: "ei" (EI/Micro) or "societe" (SAS, SASU, SARL…).

        Returns:
            List of newly created document requests.

        Raises:
            ThirdPartyNotFoundError: If the third party does not exist.
            ValueError: If entity_category is unknown.
        """
        third_party = await self._third_party_repo.get_by_id(third_party_id)
        if not third_party:
            raise ThirdPartyNotFoundError(str(third_party_id))

        requirements = REQUIREMENTS_BY_ENTITY_CATEGORY.get(entity_category)
        if requirements is None:
            raise ValueError(
                f"Catégorie d'entité inconnue : '{entity_category}'. "
                f"Valeurs acceptées : {list(REQUIREMENTS_BY_ENTITY_CATEGORY)}"
            )

        if not requirements:
            return []

        existing_docs = await self._document_repo.list_by_third_party(third_party_id)
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
                entity_category=entity_category,
                count=len(created),
                types=[d.document_type.value for d in created],
            )

        return created
