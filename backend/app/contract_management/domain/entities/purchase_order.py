"""Purchase order (bon de commande) domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contract_management.domain.exceptions import (
    FrameworkContractNotSignedError,
    InvalidPurchaseOrderStatusError,
    PurchaseOrderIncompleteError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

# Champs sans lesquels un BDC ne peut ni être généré ni signé. Le webhook
# positionnement crée volontairement un BDC incomplet (« à rattacher ») :
# c'est l'ADV qui le complète.
REQUIRED_FIELDS_FOR_GENERATION: tuple[tuple[str, str], ...] = (
    ("third_party_id", "le fournisseur"),
    ("company_id", "la société émettrice"),
    ("client_name", "le client final"),
    ("mission_title", "l'intitulé de la mission"),
    ("purchase_daily_rate", "le CJM (coût journalier d'achat)"),
    ("days_sold", "le nombre de jours vendus"),
    ("start_date", "la date de début"),
    ("end_date", "la date de fin"),
)


@dataclass
class PurchaseOrder:
    """Un bon de commande : une mission d'un consultant chez un client.

    Rattaché à un fournisseur (`third_party_id`) et au contrat cadre de ce
    fournisseur (`contract_request_id`). Un fournisseur porte N bons de
    commande dans le temps, un par consultant et par mission.

    Numérotation : ``XXX-BC-NNN``, séquence propre à chaque société émettrice,
    assignée à la création. Elle matérialise la numérotation séquentielle
    qu'exige l'article « Bon de Commande » du contrat cadre.

    Conditions financières — deux taux, deux publics :
    - ``sale_daily_rate`` (TJM) est le prix de vente au client. **Interne** :
      il ne doit jamais figurer sur le document remis au fournisseur.
    - ``purchase_daily_rate`` (CJM) est le coût d'achat payé au fournisseur.
      C'est le seul taux imprimé sur le bon de commande.
    """

    reference: str
    id: UUID = field(default_factory=uuid4)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    company_id: UUID | None = None
    third_party_id: UUID | None = None
    contract_request_id: UUID | None = None
    parent_purchase_order_id: UUID | None = None

    # Consultant
    boond_consultant_id: int | None = None
    boond_consultant_type: str | None = None  # "candidate" ou "resource"
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None

    # Origine Boond
    boond_positioning_id: int | None = None
    boond_need_id: int | None = None
    boond_delivery_id: int | None = None

    # Mission
    client_name: str | None = None
    mission_title: str | None = None
    mission_description: str | None = None
    mission_site_name: str | None = None
    mission_address: str | None = None
    mission_postal_code: str | None = None
    mission_city: str | None = None

    # Conditions financières
    sale_daily_rate: Decimal | None = None  # TJM vente — interne, jamais imprimé
    purchase_daily_rate: Decimal | None = None  # CJM achat — le taux du document
    days_sold: Decimal | None = None
    free_days: Decimal = Decimal("0")
    start_date: date | None = None
    end_date: date | None = None

    # Documents et signature
    s3_key_draft: str | None = None
    s3_key_signed: str | None = None
    yousign_envelope_id: str | None = None
    sent_for_signature_at: datetime | None = None
    signed_at: datetime | None = None

    # Synchronisation Boond
    boond_contract_id: int | None = None
    boond_purchase_order_id: int | None = None
    boond_sync_error: str | None = None

    commercial_email: str | None = None
    created_by: UUID | None = None
    status_history: list[dict[str, Any]] = field(default_factory=list)
    # NEEDS-CONFIRMATION: `datetime.utcnow()` (naïf) retenu par cohérence avec
    # le reste du contexte — les colonnes sont en TIMESTAMP WITHOUT TIME ZONE
    # et asyncpg refuse un datetime tz-aware. Cf. dette technique MEMORY.md.
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Amorce l'historique avec le statut initial (cf. ContractRequest)."""
        if not self.status_history:
            self.status_history.append(
                {
                    "status": self.status.value,
                    "entered_at": self.created_at.isoformat(),
                    "initial": True,
                }
            )

    # ── Consultant ────────────────────────────────────────────────────────

    @property
    def consultant_name(self) -> str:
        """Nom affichable du consultant."""
        parts = [self.consultant_first_name, self.consultant_last_name]
        return " ".join(p for p in parts if p).strip()

    @property
    def needs_third_party(self) -> bool:
        """BDC « à rattacher » : créé par webhook, fournisseur pas encore choisi."""
        return self.third_party_id is None

    # ── Montants ──────────────────────────────────────────────────────────

    @property
    def billable_days(self) -> Decimal:
        """Jours facturables = jours vendus moins les jours de gratuité.

        Les jours de gratuité sont des jours travaillés que le fournisseur ne
        facture pas : ils comptent dans la mission, pas dans le montant.
        Jamais négatif — une gratuité supérieure aux jours vendus est refusée
        à la saisie, la borne ici n'est qu'une sécurité d'affichage.
        """
        if self.days_sold is None:
            return Decimal("0")
        return max(Decimal("0"), self.days_sold - (self.free_days or Decimal("0")))

    @property
    def total_amount(self) -> Decimal:
        """Montant HT du bon de commande : jours facturables x CJM.

        C'est le montant imprimé sur le document et poussé dans Boond.
        """
        if self.purchase_daily_rate is None:
            return Decimal("0")
        return self.billable_days * self.purchase_daily_rate

    @property
    def estimated_margin(self) -> Decimal | None:
        """Marge indicative interne : (TJM - CJM) x jours facturables.

        ``None`` tant que le TJM de vente n'est pas renseigné. Affichée dans
        Bobby uniquement — jamais dans un document ni un email au fournisseur.
        """
        if self.sale_daily_rate is None or self.purchase_daily_rate is None:
            return None
        return (self.sale_daily_rate - self.purchase_daily_rate) * self.billable_days

    # ── Complétude ────────────────────────────────────────────────────────

    @property
    def missing_fields(self) -> list[str]:
        """Libellés des champs manquants pour générer le bon de commande."""
        return [
            label for attr, label in REQUIRED_FIELDS_FOR_GENERATION if getattr(self, attr) is None
        ]

    @property
    def is_complete(self) -> bool:
        """Le BDC a-t-il tout ce qu'il faut pour être généré ?"""
        return not self.missing_fields

    # ── Machine à états ───────────────────────────────────────────────────

    def can_transition_to(self, target: PurchaseOrderStatus) -> bool:
        """Check if the transition to target status is allowed."""
        return self.status.can_transition_to(target)

    def transition_to(self, target: PurchaseOrderStatus) -> None:
        """Perform a validated status transition.

        Raises:
            InvalidPurchaseOrderStatusError: If the transition is invalid.
        """
        if not self.can_transition_to(target):
            raise InvalidPurchaseOrderStatusError(self.status.value, target.value)
        now = datetime.utcnow()
        self.status_history.append({"status": target.value, "entered_at": now.isoformat()})
        self.status = target
        self.updated_at = now

    def mark_generated(self, s3_key_draft: str) -> None:
        """Enregistre le document généré.

        Raises:
            PurchaseOrderIncompleteError: If required mission fields are missing.
        """
        if not self.is_complete:
            raise PurchaseOrderIncompleteError(self.reference, self.missing_fields)
        self.s3_key_draft = s3_key_draft
        self.transition_to(PurchaseOrderStatus.GENERATED)

    def send_for_signature(self, *, framework_contract_signed: bool) -> None:
        """Envoie le bon de commande en signature au fournisseur.

        Le contrat cadre doit être signé : un bon de commande ne vaut que sous
        un cadre en vigueur, puisque c'est lui qui en porte les conditions
        juridiques. Le BDC reste préparable pendant la contractualisation du
        cadre, seul l'envoi est retenu.

        Raises:
            FrameworkContractNotSignedError: If the framework contract is not signed.
        """
        if not framework_contract_signed:
            raise FrameworkContractNotSignedError(self.reference)
        self.transition_to(PurchaseOrderStatus.SENT_FOR_SIGNATURE)
        self.sent_for_signature_at = datetime.utcnow()

    def mark_signed(self, s3_key_signed: str) -> None:
        """Enregistre le document signé par le fournisseur."""
        self.s3_key_signed = s3_key_signed
        self.transition_to(PurchaseOrderStatus.SIGNED)
        self.signed_at = datetime.utcnow()

    def mark_active(self) -> None:
        """Le BDC est signé et synchronisé dans Boond."""
        self.boond_sync_error = None
        self.transition_to(PurchaseOrderStatus.ACTIVE)

    def close(self) -> None:
        """Clôture le bon de commande (fin de mission)."""
        self.transition_to(PurchaseOrderStatus.CLOSED)

    def cancel(self) -> None:
        """Annule le bon de commande avant signature."""
        self.transition_to(PurchaseOrderStatus.CANCELLED)
