"""Purchase order status value object."""

from enum import Enum


class PurchaseOrderStatus(str, Enum):
    """Status of a purchase order (bon de commande)."""

    DRAFT = "draft"
    SENT = "sent"
    ACTIVE = "active"
    CLOSED = "closed"

    @property
    def display_name(self) -> str:
        """Return human-readable status label."""
        labels = {
            "draft": "Brouillon",
            "sent": "Envoyé",
            "active": "Actif",
            "closed": "Clôturé",
        }
        return labels.get(self.value, self.value)
