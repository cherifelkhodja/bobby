"""Framework contract status value object."""

from enum import Enum


class FrameworkContractStatus(str, Enum):
    """Status of a framework contract (contrat cadre)."""

    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # Within 30 days of expiration
    EXPIRED = "expired"
    TERMINATED = "terminated"

    @property
    def display_name(self) -> str:
        """Return human-readable status label."""
        labels = {
            "active": "Actif",
            "expiring_soon": "Expiration proche",
            "expired": "Expiré",
            "terminated": "Résilié",
        }
        return labels.get(self.value, self.value)

    @property
    def is_usable(self) -> bool:
        """Whether this framework contract can be used for new purchase orders."""
        return self in (FrameworkContractStatus.ACTIVE, FrameworkContractStatus.EXPIRING_SOON)
