"""Use case: Configure contract details."""

from typing import Any
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError

logger = structlog.get_logger()


class ConfigureContractUseCase:
    """Set contract configuration (payment terms, clauses, etc.)."""

    def __init__(self, contract_request_repository) -> None:
        self._cr_repo = contract_request_repository

    async def execute(self, contract_request_id: UUID, config: dict[str, Any]):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.
            config: Contract configuration dictionary.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        cr.set_contract_config(config)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_configured",
            cr_id=str(saved.id),
            config_keys=list(config.keys()),
        )
        return saved
