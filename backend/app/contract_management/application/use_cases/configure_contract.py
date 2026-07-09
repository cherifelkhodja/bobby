"""Use case: Configure contract details."""

from typing import Any
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError

logger = structlog.get_logger()

# Per-contract edition keys managed by the article-overrides endpoint. They must
# survive a `configure` call, which otherwise replaces the whole contract_config.
_EDITION_KEYS = (
    "article_overrides",
    "annex_overrides",
    "custom_articles",
    "custom_annexes",
    "article_order",
    "annex_order",
    "deleted_article_keys",
    "deleted_annex_keys",
)


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

        # company_id: only touch it when the key is present in the payload.
        # An absent key must NOT wipe an already auto-resolved company.
        if "company_id" in config:
            raw_company_id = config.get("company_id")
            if raw_company_id:
                try:
                    cr.company_id = UUID(str(raw_company_id))
                except (ValueError, AttributeError):
                    cr.company_id = None
            else:
                cr.company_id = None

        # Merge: start from the new config, then re-inject the per-contract edition
        # keys from the previous config so article/annex customisations (managed by
        # the article-overrides endpoint) are not lost.
        old_config = dict(cr.contract_config or {})
        merged = dict(config)
        for key in _EDITION_KEYS:
            if key in old_config:
                merged[key] = old_config[key]

        cr.set_contract_config(merged)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_configured",
            cr_id=str(saved.id),
            config_keys=list(merged.keys()),
        )
        return saved
