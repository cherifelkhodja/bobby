"""Port for CRM operations (BoondManager extension)."""

from typing import Any, Protocol


class CrmServicePort(Protocol):
    """Port for CRM operations related to contract management."""

    async def get_positioning(self, positioning_id: int) -> dict[str, Any] | None:
        """Fetch a positioning from the CRM.

        Args:
            positioning_id: CRM positioning ID.

        Returns:
            Positioning data or None.
        """
        ...

    async def get_need(self, need_id: int) -> dict[str, Any] | None:
        """Fetch a need/opportunity from the CRM.

        Args:
            need_id: CRM need ID.

        Returns:
            Need data or None.
        """
        ...

    async def get_candidate_info(self, candidate_id: int) -> dict[str, Any] | None:
        """Fetch candidate info from the CRM.

        Args:
            candidate_id: CRM candidate ID.

        Returns:
            Candidate data or None.
        """
        ...

    async def create_provider(
        self,
        company_name: str,
        siren: str,
        contact_email: str,
    ) -> int:
        """Create a provider in the CRM.

        Args:
            company_name: Provider company name.
            siren: SIREN number.
            contact_email: Contact email.

        Returns:
            CRM provider ID.
        """
        ...

    async def create_purchase_order(
        self,
        provider_id: int,
        positioning_id: int,
        reference: str,
        amount: float,
    ) -> int:
        """Create a purchase order in the CRM.

        Args:
            provider_id: CRM provider ID.
            positioning_id: CRM positioning ID.
            reference: Contract reference.
            amount: Order amount.

        Returns:
            CRM purchase order ID.
        """
        ...
