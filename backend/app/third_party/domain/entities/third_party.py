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

    company_name: str
    legal_form: str
    siren: str
    siret: str
    rcs_city: str
    rcs_number: str
    head_office_address: str
    representative_name: str
    representative_title: str
    contact_email: str
    type: ThirdPartyType
    id: UUID = field(default_factory=uuid4)
    boond_provider_id: int | None = None
    capital: str | None = None
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
            f"{self.legal_form} {self.company_name}",
            f"au capital de {self.capital} euros" if self.capital else None,
            f"Siège social : {self.head_office_address}",
            f"RCS {self.rcs_city} {self.rcs_number}",
        ]
        return ", ".join(p for p in parts if p)
