"""Use case: Block compliance for a contract request."""

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


class BlockComplianceUseCase:
    """Transition a contract request from REVIEWING_COMPLIANCE to COMPLIANCE_BLOCKED.

    Called by ADV when documents are deemed non-conformant after review.
    """

    ALLOWED_STATUSES = frozenset({ContractRequestStatus.REVIEWING_COMPLIANCE})

    def __init__(self, contract_request_repository) -> None:
        self._cr_repo = contract_request_repository

    async def execute(self, contract_request_id: UUID, reason: str | None = None):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.
            reason: Optional explanation of what is blocking compliance.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            InvalidContractStatusError: If the CR is not in REVIEWING_COMPLIANCE.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if cr.status not in self.ALLOWED_STATUSES:
            raise InvalidContractStatusError(cr.status.value, "reviewing_compliance")

        cr.block_compliance(reason)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "compliance_blocked",
            cr_id=str(saved.id),
            reason=reason,
        )
        return saved
