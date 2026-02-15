"""Use case: Check and update compliance status for a third party."""

from uuid import UUID

import structlog

from app.third_party.domain.exceptions import ThirdPartyNotFoundError
from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.vigilance.domain.services.compliance_checker import compute_compliance_status

logger = structlog.get_logger()


class CheckComplianceUseCase:
    """Recalculate the compliance status of a third party.

    Fetches all documents, computes the status based on requirements,
    and updates the third party if the status changed.
    """

    def __init__(self, third_party_repository, document_repository) -> None:
        self._third_party_repo = third_party_repository
        self._document_repo = document_repository

    async def execute(self, third_party_id: UUID) -> ComplianceStatus:
        """Execute the use case.

        Args:
            third_party_id: ID of the third party.

        Returns:
            The computed compliance status.

        Raises:
            ThirdPartyNotFoundError: If the third party does not exist.
        """
        third_party = await self._third_party_repo.get_by_id(third_party_id)
        if not third_party:
            raise ThirdPartyNotFoundError(str(third_party_id))

        documents = await self._document_repo.list_by_third_party(third_party_id)
        new_status = compute_compliance_status(third_party.type, documents)

        if third_party.compliance_status != new_status:
            old_status = third_party.compliance_status
            third_party.update_compliance_status(new_status)
            await self._third_party_repo.save(third_party)
            logger.info(
                "compliance_status_changed",
                third_party_id=str(third_party_id),
                old_status=old_status.value,
                new_status=new_status.value,
            )

        return new_status
