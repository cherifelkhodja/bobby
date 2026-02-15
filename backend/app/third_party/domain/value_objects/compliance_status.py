"""Compliance status value object."""

from enum import Enum


class ComplianceStatus(str, Enum):
    """Overall compliance status of a third party's document portfolio."""

    PENDING = "pending"
    COMPLIANT = "compliant"
    EXPIRING_SOON = "expiring_soon"
    NON_COMPLIANT = "non_compliant"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable status name."""
        names = {
            ComplianceStatus.PENDING: "Dossier en cours",
            ComplianceStatus.COMPLIANT: "Conforme",
            ComplianceStatus.EXPIRING_SOON: "Expiration proche",
            ComplianceStatus.NON_COMPLIANT: "Non conforme",
        }
        return names[self]

    @property
    def allows_contract_generation(self) -> bool:
        """Check if compliance status allows contract generation."""
        return self == ComplianceStatus.COMPLIANT
