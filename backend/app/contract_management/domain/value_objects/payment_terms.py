"""Payment terms and invoice method value objects."""

from enum import Enum


class PaymentTerms(str, Enum):
    """Payment terms for contracts."""

    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    END_OF_MONTH_30 = "end_of_month_30"
    END_OF_MONTH_45 = "end_of_month_45"

    @property
    def display_text(self) -> str:
        """Return text for contract generation."""
        mapping = {
            "net_30": "30 jours nets",
            "net_45": "45 jours nets",
            "net_60": "60 jours nets",
            "end_of_month_30": "30 jours fin de mois",
            "end_of_month_45": "45 jours fin de mois",
        }
        return mapping.get(self.value, self.value)


class InvoiceSubmissionMethod(str, Enum):
    """Invoice submission method."""

    EMAIL = "email"
    PLATFORM = "platform"
    POSTAL = "postal"

    @property
    def display_text(self) -> str:
        """Return text for contract generation."""
        mapping = {
            "email": "par email",
            "platform": "via la plateforme de facturation",
            "postal": "par voie postale",
        }
        return mapping.get(self.value, self.value)
