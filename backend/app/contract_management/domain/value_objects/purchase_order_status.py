"""Purchase order (bon de commande) status value object with state machine."""

from enum import Enum


class PurchaseOrderStatus(str, Enum):
    """Status of a purchase order through its lifecycle.

    Un BDC naît en ``DRAFT`` — créé par le webhook positionnement (sans
    fournisseur, « à rattacher ») ou saisi par l'ADV — puis suit un parcours
    linéaire jusqu'à ``CLOSED``. Il peut être annulé tant qu'il n'est pas signé.
    """

    DRAFT = "draft"
    GENERATED = "generated"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"

    @property
    def allowed_transitions(self) -> frozenset["PurchaseOrderStatus"]:
        """Return valid transitions from this status."""
        transitions = {
            PurchaseOrderStatus.DRAFT: frozenset(
                {
                    PurchaseOrderStatus.GENERATED,
                    PurchaseOrderStatus.CANCELLED,
                }
            ),
            PurchaseOrderStatus.GENERATED: frozenset(
                {
                    PurchaseOrderStatus.SENT_FOR_SIGNATURE,
                    # Régénération après correction : le BDC repasse par DRAFT
                    # dès qu'un champ de la mission change.
                    PurchaseOrderStatus.DRAFT,
                    PurchaseOrderStatus.GENERATED,
                    PurchaseOrderStatus.CANCELLED,
                }
            ),
            PurchaseOrderStatus.SENT_FOR_SIGNATURE: frozenset(
                {
                    PurchaseOrderStatus.SIGNED,
                    # Renvoi après correction (le fournisseur n'a pas signé).
                    PurchaseOrderStatus.GENERATED,
                    PurchaseOrderStatus.CANCELLED,
                }
            ),
            # SIGNED → ACTIVE est porté par la synchronisation Boond : un BDC
            # signé mais non synchronisé reste visible comme tel.
            PurchaseOrderStatus.SIGNED: frozenset({PurchaseOrderStatus.ACTIVE}),
            PurchaseOrderStatus.ACTIVE: frozenset({PurchaseOrderStatus.CLOSED}),
            PurchaseOrderStatus.CLOSED: frozenset(),
            PurchaseOrderStatus.CANCELLED: frozenset(),
        }
        return transitions.get(self, frozenset())

    def can_transition_to(self, target: "PurchaseOrderStatus") -> bool:
        """Check if transition to target status is allowed."""
        return target in self.allowed_transitions

    @property
    def is_editable(self) -> bool:
        """Le BDC accepte-t-il encore des modifications de sa mission ?"""
        return self in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.GENERATED)

    @property
    def is_final(self) -> bool:
        """Le BDC a-t-il atteint un état terminal ?"""
        return self in (PurchaseOrderStatus.CLOSED, PurchaseOrderStatus.CANCELLED)

    @property
    def display_name(self) -> str:
        """Return human-readable status label."""
        labels = {
            "draft": "Brouillon",
            "generated": "Bon de commande généré",
            "sent_for_signature": "Envoyé en signature",
            "signed": "Signé",
            "active": "Actif",
            "closed": "Clôturé",
            "cancelled": "Annulé",
        }
        return labels.get(self.value, self.value)
