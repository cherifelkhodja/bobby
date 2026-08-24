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

    async def get_candidate_info(
        self,
        candidate_id: int,
        consultant_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch consultant info from the CRM.

        Args:
            candidate_id: Boond candidate or resource ID.
            consultant_type: "candidate", "resource", or None (unknown) —
                oriente le routage vers /candidates ou /resources.
        """
        ...

    async def positioning_states(self) -> dict[int, str]:
        """CRM-configured positioning states, as ``{value: label}``."""
        ...

    async def update_positioning_state(self, positioning_id: int, state: int) -> int | None:
        """Change l'état d'un positionnement (« Gagné » crée la prestation).

        Renvoie l'état que le CRM confirme, quand il en confirme un.
        """
        ...

    async def resolve_resource_id(self, candidate_id: int) -> int | None:
        """Resolve the Boond resource ID linked to a candidate ID (or None)."""
        ...

    async def candidate_exists(self, candidate_id: int) -> bool:
        """Cet identifiant est-il celui d'un candidat ?"""
        ...

    async def resource_exists(self, resource_id: int) -> bool:
        """Cet identifiant est-il celui d'une ressource ?

        Candidats et ressources ont deux séries d'identifiants : le même numéro
        peut désigner deux personnes. À n'interroger qu'une fois établi que le
        numéro n'est pas celui d'un candidat.
        """
        ...

    async def create_provider(
        self,
        company_name: str,
        siren: str,
        contact_email: str,
    ) -> int:
        """Create a minimal provider in the CRM."""
        ...

    async def create_supplier_purchase(
        self,
        delivery_id: int,
        title: str,
        provider_id: int | None = None,
        provider_contact_id: int | None = None,
        reference: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        vat_liable: bool = True,
    ) -> int:
        """Create the supplier purchase attached to a delivery. Returns its ID."""
        ...

    async def delete_supplier_purchase(self, purchase_id: int) -> bool:
        """Delete a supplier purchase. True once it is gone."""
        ...

    async def delete_boond_contract(self, contract_id: int) -> bool:
        """Delete a CRM contract. True once it is gone."""
        ...

    async def delete_delivery(self, delivery_id: int) -> bool:
        """Delete a delivery. True once it is gone."""
        ...

    async def create_purchase_order(
        self,
        provider_id: int,
        positioning_id: int,
        reference: str,
        amount: float,
    ) -> int:
        """Create a purchase order in the CRM (ancienne méthode, adossée au contrat cadre)."""
        ...

    async def convert_candidate_to_resource(
        self,
        candidate_id: int,
        state: int = 3,
        state_reason_type_of: int | None = None,
        type_of: int | None = None,
        manager_id: int | None = None,
    ) -> int:
        """Convert a candidate to a resource. Returns the new resource ID."""
        ...

    async def update_company_information(
        self,
        company_id: int,
        postcode: str | None = None,
        address: str | None = None,
        town: str | None = None,
        country: str | None = None,
        legal_status: str | None = None,
        registered_office: str | None = None,
    ) -> None:
        """Update company information in CRM."""
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
        start_date: str | None = None,
        end_date: str | None = None,
        agency_id: int | None = None,
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

    async def verify_company_exists(self, company_id: int) -> bool:
        """Check whether a company exists in the CRM."""
        ...

    async def update_company_bank_details(
        self,
        company_id: int,
        iban: str,
        bic: str,
        description: str = "RIB Fournisseur",
    ) -> None:
        """Push bank details (IBAN/BIC) to a company in the CRM."""
        ...
