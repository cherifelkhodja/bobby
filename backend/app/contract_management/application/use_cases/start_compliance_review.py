"""Use case: Start compliance review for a contract request."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class StartComplianceReviewUseCase:
    """Transition a contract request from COLLECTING_DOCUMENTS to REVIEWING_COMPLIANCE.

    Called manually by ADV when they want to start reviewing the documents
    submitted by the third party, or automatically when the third party
    clicks 'Valider le dépôt' on the portal.
    """

    ALLOWED_STATUSES = frozenset({ContractRequestStatus.COLLECTING_DOCUMENTS})

    def __init__(self, contract_request_repository) -> None:
        self._cr_repo = contract_request_repository

    async def execute(self, contract_request_id: UUID):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            InvalidContractStatusError: If the CR is not in COLLECTING_DOCUMENTS.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if cr.status not in self.ALLOWED_STATUSES:
            raise InvalidContractStatusError(cr.status.value, "collecting_documents")

        cr.start_compliance_review()
        saved = await self._cr_repo.save(cr)

        logger.info(
            "compliance_review_started",
            cr_id=str(saved.id),
        )
        return saved
