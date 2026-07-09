"""Port for contract management repositories."""

from typing import Protocol
from uuid import UUID

from app.contract_management.domain.entities.contract import Contract
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


class ContractRequestRepositoryPort(Protocol):
    """Repository port for contract requests."""

    async def get_by_id(self, request_id: UUID) -> ContractRequest | None:
        """Get a contract request by ID."""
        ...

    async def get_by_positioning_id(self, positioning_id: int) -> ContractRequest | None:
        """Get a contract request by Boond positioning ID."""
        ...

    async def save(self, request: ContractRequest) -> ContractRequest:
        """Save a contract request (create or update)."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        status: ContractRequestStatus | None = None,
    ) -> list[ContractRequest]:
        """List contract requests with optional status filter."""
        ...

    async def count(self, status: ContractRequestStatus | None = None) -> int:
        """Count contract requests with optional status filter."""
        ...

    async def get_next_provisional_reference(self) -> str:
        """Generate the next provisional reference (e.g. PROV-2026-0042).

        Assigned at creation. Independent counter from the final reference.
        """
        ...

    async def get_next_reference(self, company_code: str | None = None) -> str:
        """Generate the next final contract reference (e.g. GEM-CC-0001).

        Assigned at PARTNER_APPROVED. Starts with the 3-letter company code.

        Args:
            company_code: 2-3 letter company prefix. If None, the default
                          company's code is used (falls back to "GEN").
        """
        ...

    async def get_latest_by_resource_id(self, resource_id: int) -> ContractRequest | None:
        """Get the latest contract request for a Boond resource ID.

        Used for re-contractualization to pre-fill data from a previous request.
        """
        ...

    async def get_company_by_boond_agency_id(self, agency_id: int) -> UUID | None:
        """Return the contract company ID matching a Boond agency ID, or None."""
        ...

    async def get_company_code(self, company_id: UUID) -> str | None:
        """Return the code of a contract company by ID, or None."""
        ...


class ContractRepositoryPort(Protocol):
    """Repository port for contracts."""

    async def get_by_id(self, contract_id: UUID) -> Contract | None:
        """Get a contract by ID."""
        ...

    async def get_by_request_id(self, request_id: UUID) -> Contract | None:
        """Get the latest contract for a request."""
        ...

    async def list_by_contract_request(self, request_id: UUID) -> list[Contract]:
        """List all contracts for a contract request, ordered by version."""
        ...

    async def save(self, contract: Contract) -> Contract:
        """Save a contract (create or update)."""
        ...


class WebhookEventRepositoryPort(Protocol):
    """Repository port for webhook event deduplication."""

    async def exists(self, event_id: str) -> bool:
        """Check if a webhook event has already been processed."""
        ...

    async def save(self, event_id: str, event_type: str, payload: dict) -> None:
        """Save a webhook event for deduplication."""
        ...

    async def delete_by_prefix(self, prefix: str) -> int:
        """Delete webhook events whose ID starts with the given prefix.

        Returns:
            The number of deleted rows.
        """
        ...
