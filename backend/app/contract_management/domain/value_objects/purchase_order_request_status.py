"""Purchase order request status value object with state machine."""

from enum import Enum


class PurchaseOrderRequestStatus(str, Enum):
    """Status of a purchase order request through its lifecycle.

    Simplified workflow for creating a BDC when a framework contract
    already exists for the supplier.
    """

    # Verrouillé : le BDC existe (positionnement gagné) mais n'est pas encore
    # éditable car le consultant n'est pas une ressource rattachée à un contrat
    # cadre actif. Déverrouillé (→ PENDING_VALIDATION) à la signature du cadre.
    PENDING_FRAMEWORK_CONTRACT = "pending_framework_contract"
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    CHECKING_COMPLIANCE = "checking_compliance"
    COMPLIANCE_EXPIRED = "compliance_expired"
    ACTIVE = "active"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

    @property
    def allowed_transitions(self) -> frozenset["PurchaseOrderRequestStatus"]:
        """Return valid transitions from this status."""
        t = {
            PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT: frozenset(
                {
                    PurchaseOrderRequestStatus.PENDING_VALIDATION,
                    PurchaseOrderRequestStatus.CANCELLED,
                }
            ),
            PurchaseOrderRequestStatus.PENDING_VALIDATION: frozenset(
                {
                    PurchaseOrderRequestStatus.VALIDATED,
                    PurchaseOrderRequestStatus.CANCELLED,
                }
            ),
            PurchaseOrderRequestStatus.VALIDATED: frozenset(
                {
                    PurchaseOrderRequestStatus.CHECKING_COMPLIANCE,
                    PurchaseOrderRequestStatus.CANCELLED,
                }
            ),
            PurchaseOrderRequestStatus.CHECKING_COMPLIANCE: frozenset(
                {
                    PurchaseOrderRequestStatus.ACTIVE,
                    PurchaseOrderRequestStatus.COMPLIANCE_EXPIRED,
                    PurchaseOrderRequestStatus.CANCELLED,
                }
            ),
            PurchaseOrderRequestStatus.COMPLIANCE_EXPIRED: frozenset(
                {
                    PurchaseOrderRequestStatus.CHECKING_COMPLIANCE,
                    PurchaseOrderRequestStatus.CANCELLED,
                }
            ),
            PurchaseOrderRequestStatus.ACTIVE: frozenset(
                {
                    PurchaseOrderRequestStatus.ARCHIVED,
                }
            ),
            PurchaseOrderRequestStatus.ARCHIVED: frozenset(),
            PurchaseOrderRequestStatus.CANCELLED: frozenset(),
        }
        return t.get(self, frozenset())

    def can_transition_to(self, target: "PurchaseOrderRequestStatus") -> bool:
        """Check if transition to target status is allowed."""
        return target in self.allowed_transitions

    @property
    def is_editable(self) -> bool:
        """Whether the BDC can be edited/validated by the commercial.

        A BDC locked on the framework contract (or already terminal) is not
        editable.
        """
        return self not in (
            PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT,
            PurchaseOrderRequestStatus.ARCHIVED,
            PurchaseOrderRequestStatus.CANCELLED,
        )

    @property
    def display_name(self) -> str:
        """Return human-readable status label."""
        labels = {
            "pending_framework_contract": "En attente contrat cadre",
            "pending_validation": "En attente validation",
            "validated": "Validé",
            "checking_compliance": "Vérification conformité",
            "compliance_expired": "Documents expirés",
            "active": "En cours",
            "archived": "Archivé",
            "cancelled": "Annulé",
        }
        return labels.get(self.value, self.value)
