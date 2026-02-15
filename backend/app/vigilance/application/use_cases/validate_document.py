"""Use case: Validate a vigilance document."""

from datetime import datetime, timedelta
from uuid import UUID

import structlog

from app.vigilance.domain.exceptions import DocumentNotFoundError
from app.vigilance.domain.services.compliance_checker import compute_compliance_status
from app.vigilance.domain.services.vigilance_requirements import VIGILANCE_REQUIREMENTS

logger = structlog.get_logger()


class ValidateDocumentUseCase:
    """Validate a document submitted by a third party.

    Transitions the document to VALIDATED, sets the expiration date
    based on the requirements, and recalculates compliance status.
    """

    def __init__(
        self,
        document_repository,
        third_party_repository,
    ) -> None:
        self._document_repo = document_repository
        self._third_party_repo = third_party_repository

    async def execute(
        self,
        document_id: UUID,
        validated_by: str,
    ):
        """Execute the use case.

        Args:
            document_id: ID of the document to validate.
            validated_by: Email or name of the validator.

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

        # Compute expiration based on requirements
        expires_at = self._compute_expiration(third_party.type, document.document_type)

        document.validate(validated_by=validated_by, expires_at=expires_at)
        saved = await self._document_repo.save(document)

        # Recalculate compliance
        all_docs = await self._document_repo.list_by_third_party(document.third_party_id)
        new_status = compute_compliance_status(third_party.type, all_docs)
        if third_party.compliance_status != new_status:
            third_party.update_compliance_status(new_status)
            await self._third_party_repo.save(third_party)
            logger.info(
                "compliance_status_updated",
                third_party_id=str(third_party.id),
                new_status=new_status.value,
            )

        logger.info(
            "document_validated",
            document_id=str(saved.id),
            validated_by=validated_by,
            expires_at=str(expires_at) if expires_at else None,
        )
        return saved

    def _compute_expiration(self, third_party_type, document_type) -> datetime | None:
        """Compute the expiration date based on vigilance requirements.

        Args:
            third_party_type: Type of the third party.
            document_type: Type of the document.

        Returns:
            Expiration datetime or None if no expiry.
        """
        requirements = VIGILANCE_REQUIREMENTS.get(third_party_type, [])
        for req in requirements:
            if req["type"] == document_type and req["validity_months"]:
                return datetime.utcnow() + timedelta(days=req["validity_months"] * 30)
        return None
