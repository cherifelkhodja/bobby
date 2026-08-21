"""Contract request domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contract_management.domain.exceptions import InvalidContractStatusError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


@dataclass
class ContractRequest:
    """A contract request triggered by a Boond positioning.

    Follows a state machine with 14 statuses from webhook reception
    through to archival.

    Numérotation :
    - `provisional_reference` (PROV-YYYY-NNNN) : assignée à la création, sert
      d'identifiant interne tout au long du processus.
    - `reference` (XXX-CC-NNNN) : référence définitive assignée uniquement
      lorsque le partenaire approuve le contrat (état PARTNER_APPROVED).
      XXX = code société, CC = contrat cadre, NNN = numéro séquentiel.
      NULL jusqu'à ce stade.
    - `display_reference` : propriété calculée — retourne `reference` si définie,
      sinon `provisional_reference`. À utiliser pour l'affichage et les emails.
    """

    provisional_reference: str
    id: UUID = field(default_factory=uuid4)
    reference: str | None = None
    trigger_type: str | None = None  # positioning_7, candidat_11, ressource_4, ressource_5
    previous_contract_request_id: UUID | None = None
    boond_positioning_id: int | None = None
    boond_candidate_id: int | None = None
    boond_consultant_type: str | None = None  # "candidate" ou "resource"
    boond_need_id: int | None = None
    boond_resource_id: int | None = None
    commercial_email: str | None = None
    third_party_id: UUID | None = None
    status: ContractRequestStatus = ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION
    third_party_type: str | None = None
    daily_rate: Decimal | None = None
    quantity_sold: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    client_name: str | None = None
    mission_title: str | None = None
    mission_description: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None
    mission_site_name: str | None = None
    mission_address: str | None = None
    mission_postal_code: str | None = None
    mission_city: str | None = None
    contractualization_contact_email: str | None = None
    contract_config: dict[str, Any] | None = None
    company_id: UUID | None = None
    commercial_validated_at: datetime | None = None
    compliance_override: bool = False
    # Double usage assumé (aucune colonne dédiée en base) : ce champ contient
    # SOIT le motif de blocage conformité (écrit par `block_compliance`), SOIT
    # la justification d'un passage en force (écrit par `override_compliance`).
    # Le booléen `compliance_override` ci-dessus lève l'ambiguïté :
    #   - True  -> `compliance_override_reason` = justification de l'override
    #   - False -> `compliance_override_reason` = motif de blocage (COMPLIANCE_BLOCKED)
    compliance_override_reason: str | None = None
    # Dépôt des documents de vigilance volontairement ignoré (saisie manuelle
    # « en personne » : l'ADV renseigne tout sans solliciter le fournisseur).
    # Aucun emplacement de document n'est créé et la conformité est levée par
    # dérogation tracée (cf. `skip_document_collection`).
    documents_skipped: bool = False
    status_history: list[dict[str, Any]] = field(default_factory=list)
    # NEEDS-CONFIRMATION: `datetime.utcnow()` est déprécié mais conservé
    # volontairement. Les colonnes DB correspondantes sont de type
    # TIMESTAMP WITHOUT TIME ZONE (naïf) ; asyncpg refuse un datetime tz-aware
    # sur ces colonnes. Migrer vers `datetime.now(UTC)` imposerait de basculer
    # d'abord ces colonnes en `timezone=True` (changement de schéma, hors scope).
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Amorce l'historique avec le statut initial.

        Garantit que `status_history` n'est jamais vide : la timeline dispose
        d'un point de départ et `rollback_to_previous_status` retrouve le
        statut précédent dès la première transition. N'ajoute rien si
        l'historique est déjà renseigné (entité rechargée depuis la base),
        afin de ne pas dupliquer d'entrées.
        """
        if not self.status_history:
            self.status_history.append(
                {
                    "status": self.status.value,
                    "entered_at": self.created_at.isoformat(),
                    "initial": True,
                }
            )

    @property
    def display_reference(self) -> str:
        """Référence à afficher : définitive si assignée, provisoire sinon."""
        return self.reference or self.provisional_reference

    def can_transition_to(self, target: ContractRequestStatus) -> bool:
        """Check if the transition to target status is allowed."""
        return self.status.can_transition_to(target)

    def transition_to(self, target: ContractRequestStatus) -> None:
        """Perform a validated status transition.

        Args:
            target: The new status.

        Raises:
            InvalidContractStatusError: If the transition is invalid.
        """
        if not self.can_transition_to(target):
            raise InvalidContractStatusError(self.status.value, target.value)
        now = datetime.utcnow()
        self.status_history.append({"status": target.value, "entered_at": now.isoformat()})
        self.status = target
        self.updated_at = now

    def validate_commercial(
        self,
        *,
        third_party_type: str,
        contact_email: str,
    ) -> None:
        """Apply commercial validation data and transition status.

        Simplified for contrat cadre: only type tiers + contact.
        Mission-specific data (TJM, dates, address) belongs to BDC.
        """
        self.third_party_type = third_party_type
        self.contractualization_contact_email = contact_email
        self.commercial_validated_at = datetime.utcnow()
        self.transition_to(ContractRequestStatus.COMMERCIAL_VALIDATED)

    def redirect_to_payfit(self) -> None:
        """Redirect to PayFit for salarié type."""
        self.transition_to(ContractRequestStatus.REDIRECTED_PAYFIT)

    def start_compliance_review(self) -> None:
        """Mark contract as under compliance review by ADV.

        Transitions from COLLECTING_DOCUMENTS to REVIEWING_COMPLIANCE.
        """
        self.transition_to(ContractRequestStatus.REVIEWING_COMPLIANCE)

    def block_compliance(self, reason: str | None = None) -> None:
        """Block compliance due to non-conformant documents.

        Transitions from REVIEWING_COMPLIANCE to COMPLIANCE_BLOCKED.

        Args:
            reason: Optional explanation of what is blocking compliance.

        Note:
            `reason` est stocké dans le champ partagé `compliance_override_reason`.
            Comme `compliance_override` reste False, la lecture sait qu'il s'agit
            d'un motif de blocage et non d'une justification d'override.
        """
        if reason:
            self.compliance_override_reason = reason
        self.transition_to(ContractRequestStatus.COMPLIANCE_BLOCKED)

    def set_contract_config(self, config: dict[str, Any]) -> None:
        """Set contract configuration (no status transition).

        Config is now applied inline before draft generation,
        without a dedicated CONFIGURING_CONTRACT status.

        Args:
            config: Contract configuration dictionary.
        """
        self.contract_config = config
        self.updated_at = datetime.utcnow()

    def override_compliance(self, reason: str) -> None:
        """Override compliance check with a reason.

        Args:
            reason: Justification for the override.

        Note:
            Positionne `compliance_override=True` puis stocke `reason` dans le
            champ partagé `compliance_override_reason` (ici : justification de
            l'override ; cf. `block_compliance` pour l'usage « motif de blocage »).
        """
        self.compliance_override = True
        self.compliance_override_reason = reason
        self.updated_at = datetime.utcnow()

    def skip_document_collection(self, reason: str) -> None:
        """Ignorer le dépôt des documents de vigilance (saisie manuelle ADV).

        Utilisé quand le contrat est saisi « en personne », sans passer par le
        portail fournisseur : l'ADV atteste que la vigilance est traitée hors
        Bobby et ne veut pas de collecte documentaire.

        Marque la demande comme sans collecte, trace la justification via la
        dérogation de conformité existante (ce qui débloque la génération du
        brouillon) et, si la collecte est en cours, avance jusqu'à la revue de
        conformité pour que le brouillon soit générable immédiatement.

        Args:
            reason: Justification, tracée dans `compliance_override_reason`.
        """
        self.documents_skipped = True
        self.override_compliance(reason)
        if self.status == ContractRequestStatus.COLLECTING_DOCUMENTS:
            self.transition_to(ContractRequestStatus.REVIEWING_COMPLIANCE)

    def restore_document_collection(self) -> None:
        """Rétablir le dépôt des documents après un `skip_document_collection`.

        Annule la dérogation posée par le saut et ramène la demande en collecte
        si elle n'a pas encore dépassé la revue de conformité — l'ADV peut alors
        déposer les documents normalement.
        """
        self.documents_skipped = False
        self.compliance_override = False
        self.compliance_override_reason = None
        if self.status in (
            ContractRequestStatus.REVIEWING_COMPLIANCE,
            ContractRequestStatus.COMPLIANCE_BLOCKED,
        ):
            self.transition_to(ContractRequestStatus.COLLECTING_DOCUMENTS)
        self.updated_at = datetime.utcnow()

    def rollback_to_previous_status(self) -> None:
        """Rollback to the previous status in history (admin/testing only).

        Non destructif : plutôt que de supprimer l'entrée courante, on recherche
        le dernier statut distinct dans l'historique et on ajoute une nouvelle
        entrée traçant le rollback (clé ``rollback``). La timeline conserve ainsi
        l'intégralité des transitions à des fins d'audit, et la dernière entrée
        reflète toujours le statut courant.

        Raises:
            InvalidContractStatusError: If there is no previous status.
        """
        previous_status: ContractRequestStatus | None = None
        for entry in reversed(self.status_history):
            entry_status = entry.get("status")
            if entry_status and entry_status != self.status.value:
                previous_status = ContractRequestStatus(entry_status)
                break

        if previous_status is None:
            raise InvalidContractStatusError(self.status.value, "no previous status in history")

        now = datetime.utcnow()
        self.status_history.append(
            {
                "status": previous_status.value,
                "entered_at": now.isoformat(),
                "rollback": True,
                "rolled_back_from": self.status.value,
            }
        )
        self.status = previous_status
        self.updated_at = now
