"""Third party domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType


@dataclass
class ThirdParty:
    """Represents a freelance or subcontractor.

    Stores only data that BoondManager does not manage:
    legal identity, compliance status, contractualization contact.
    """

    contact_email: str
    type: ThirdPartyType
    company_name: str | None = None
    legal_form: str | None = None
    siren: str | None = None
    siret: str | None = None
    rcs_city: str | None = None
    rcs_number: str | None = None
    head_office_address: str | None = None
    representative_name: str | None = None
    representative_title: str | None = None
    # Structured representative fields
    representative_civility: str | None = None
    representative_first_name: str | None = None
    representative_last_name: str | None = None
    representative_email: str | None = None
    representative_phone: str | None = None
    # Signatory
    signatory_civility: str | None = None
    signatory_first_name: str | None = None
    signatory_last_name: str | None = None
    signatory_email: str | None = None
    signatory_phone: str | None = None
    # ADV contact
    adv_contact_civility: str | None = None
    adv_contact_first_name: str | None = None
    adv_contact_last_name: str | None = None
    adv_contact_email: str | None = None
    adv_contact_phone: str | None = None
    # Billing contact
    billing_contact_civility: str | None = None
    billing_contact_first_name: str | None = None
    billing_contact_last_name: str | None = None
    billing_contact_email: str | None = None
    billing_contact_phone: str | None = None
    id: UUID = field(default_factory=uuid4)
    boond_provider_id: int | None = None
    capital: str | None = None
    entity_category: str | None = None  # "ei" or "societe", set when portal company-info is submitted
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_compliance_status(self, new_status: ComplianceStatus) -> None:
        """Update the compliance status of this third party.

        Args:
            new_status: The new compliance status.
        """
        self.compliance_status = new_status
        self.updated_at = datetime.utcnow()

    @property
    def is_compliant(self) -> bool:
        """Check if the third party is fully compliant."""
        return self.compliance_status == ComplianceStatus.COMPLIANT

    @property
    def full_legal_identity(self) -> str:
        """Return formatted legal identity string."""
        parts = [
            f"{self.legal_form} {self.company_name}" if self.legal_form and self.company_name else None,
            f"au capital de {self.capital} euros" if self.capital else None,
            f"Siège social : {self.head_office_address}" if self.head_office_address else None,
            f"RCS {self.rcs_city} {self.rcs_number}" if self.rcs_city and self.rcs_number else None,
        ]
        return ", ".join(p for p in parts if p)
