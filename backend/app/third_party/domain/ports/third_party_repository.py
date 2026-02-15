"""Third party repository port."""

from typing import Protocol
from uuid import UUID

from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.value_objects.compliance_status import ComplianceStatus


class ThirdPartyRepositoryPort(Protocol):
    """Port for third party persistence operations."""

    async def get_by_id(self, third_party_id: UUID) -> ThirdParty | None:
        """Get third party by ID."""
        ...

    async def get_by_siren(self, siren: str) -> ThirdParty | None:
        """Get third party by SIREN number."""
        ...

    async def save(self, third_party: ThirdParty) -> ThirdParty:
        """Save third party (create or update)."""
        ...

    async def delete(self, third_party_id: UUID) -> bool:
        """Delete third party by ID."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        compliance_status: ComplianceStatus | None = None,
        search: str | None = None,
        third_party_type: str | None = None,
    ) -> list[ThirdParty]:
        """List third parties with optional filters."""
        ...

    async def count(
        self,
        compliance_status: ComplianceStatus | None = None,
        search: str | None = None,
        third_party_type: str | None = None,
    ) -> int:
        """Count third parties with optional filters."""
        ...

    async def count_by_compliance(self) -> dict[str, int]:
        """Count third parties grouped by compliance status.

        Returns:
            Dict with compliance status as key and count as value.
        """
        ...
