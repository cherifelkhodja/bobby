"""Port for CRM operations (BoondManager extension)."""

from typing import Any, Protocol


class CrmServicePort(Protocol):
    """Port for CRM operations related to contract management."""

    async def get_positioning(self, positioning_id: int) -> dict[str, Any] | None:
        """Fetch a positioning from the CRM."""
        ...

    async def get_need(self, need_id: int) -> dict[str, Any] | None:
        """Fetch a need/opportunity from the CRM."""
        ...

    async def get_candidate_info(self, candidate_id: int) -> dict[str, Any] | None:
        """Fetch candidate info from the CRM."""
        ...

    async def create_provider(
        self,
        company_name: str,
        siren: str,
        contact_email: str,
    ) -> int:
        """Create a minimal provider in the CRM."""
        ...

    async def create_purchase_order(
        self,
        provider_id: int,
        positioning_id: int,
        reference: str,
        amount: float,
    ) -> int:
        """Create a purchase order in the CRM."""
        ...

    async def convert_candidate_to_resource(
        self,
        candidate_id: int,
        state: int = 3,
    ) -> None:
        """Convert a candidate to a resource by updating their state."""
        ...

    async def create_company_full(
        self,
        company_name: str,
        state: int,
        postcode: str | None,
        address: str | None,
        town: str | None,
        country: str,
        vat_number: str | None,
        siret: str | None,
        legal_status: str | None,
        registered_office: str | None,
        ape_code: str,
        agency_id: int | None,
    ) -> int:
        """Create a provider company with full details."""
        ...

    async def create_contact(
        self,
        company_id: int,
        civility: str | None,
        first_name: str | None,
        last_name: str | None,
        email: str | None,
        phone: str | None,
        job_title: str | None,
        types_of: list[int] | None = None,
        postcode: str | None = None,
        address: str | None = None,
        town: str | None = None,
        agency_id: int | None = None,
    ) -> int:
        """Create a contact linked to a company."""
        ...

    async def get_resource_type_of(self, resource_id: int) -> int | None:
        """Fetch the typeOf attribute of a resource (0=salarié, 1=externe)."""
        ...

    async def create_boond_contract(
        self,
        resource_id: int,
        positioning_id: int,
        daily_rate: float,
        type_of: int,
    ) -> int:
        """Create a contract in the CRM for an external consultant."""
        ...

    async def update_resource_administrative(
        self,
        resource_id: int,
        provider_company_id: int,
        provider_contact_id: int | None,
    ) -> None:
        """Link a resource to its provider company and contact."""
        ...
