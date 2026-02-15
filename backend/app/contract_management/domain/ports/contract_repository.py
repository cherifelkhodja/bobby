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

    async def get_next_reference(self) -> str:
        """Generate the next contract request reference (e.g. CR-2026-0042)."""
        ...


class ContractRepositoryPort(Protocol):
    """Repository port for contracts."""

    async def get_by_id(self, contract_id: UUID) -> Contract | None:
        """Get a contract by ID."""
        ...

    async def get_by_request_id(self, request_id: UUID) -> Contract | None:
        """Get the latest contract for a request."""
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
