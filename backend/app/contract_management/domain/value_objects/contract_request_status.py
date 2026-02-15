"""Contract request status value object with state machine."""

from enum import Enum


class ContractRequestStatus(str, Enum):
    """Status of a contract request through its lifecycle."""

    PENDING_COMMERCIAL_VALIDATION = "pending_commercial_validation"
    COMMERCIAL_VALIDATED = "commercial_validated"
    COLLECTING_DOCUMENTS = "collecting_documents"
    COMPLIANCE_BLOCKED = "compliance_blocked"
    CONFIGURING_CONTRACT = "configuring_contract"
    DRAFT_GENERATED = "draft_generated"
    DRAFT_SENT_TO_PARTNER = "draft_sent_to_partner"
    PARTNER_APPROVED = "partner_approved"
    PARTNER_REQUESTED_CHANGES = "partner_requested_changes"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    ARCHIVED = "archived"
    REDIRECTED_PAYFIT = "redirected_payfit"
    CANCELLED = "cancelled"

    @property
    def allowed_transitions(self) -> frozenset["ContractRequestStatus"]:
        """Return valid transitions from this status."""
        t = {
            ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION: frozenset({
                ContractRequestStatus.COMMERCIAL_VALIDATED,
                ContractRequestStatus.REDIRECTED_PAYFIT,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.COMMERCIAL_VALIDATED: frozenset({
                ContractRequestStatus.COLLECTING_DOCUMENTS,
                ContractRequestStatus.CONFIGURING_CONTRACT,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.COLLECTING_DOCUMENTS: frozenset({
                ContractRequestStatus.CONFIGURING_CONTRACT,
                ContractRequestStatus.COMPLIANCE_BLOCKED,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.COMPLIANCE_BLOCKED: frozenset({
                ContractRequestStatus.CONFIGURING_CONTRACT,
                ContractRequestStatus.COLLECTING_DOCUMENTS,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.CONFIGURING_CONTRACT: frozenset({
                ContractRequestStatus.DRAFT_GENERATED,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.DRAFT_GENERATED: frozenset({
                ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
                ContractRequestStatus.CONFIGURING_CONTRACT,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER: frozenset({
                ContractRequestStatus.PARTNER_APPROVED,
                ContractRequestStatus.PARTNER_REQUESTED_CHANGES,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.PARTNER_APPROVED: frozenset({
                ContractRequestStatus.SENT_FOR_SIGNATURE,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.PARTNER_REQUESTED_CHANGES: frozenset({
                ContractRequestStatus.CONFIGURING_CONTRACT,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.SENT_FOR_SIGNATURE: frozenset({
                ContractRequestStatus.SIGNED,
                ContractRequestStatus.CANCELLED,
            }),
            ContractRequestStatus.SIGNED: frozenset({
                ContractRequestStatus.ARCHIVED,
            }),
            ContractRequestStatus.ARCHIVED: frozenset(),
            ContractRequestStatus.REDIRECTED_PAYFIT: frozenset(),
            ContractRequestStatus.CANCELLED: frozenset(),
        }
        return t.get(self, frozenset())

    def can_transition_to(self, target: "ContractRequestStatus") -> bool:
        """Check if transition to target status is allowed."""
        return target in self.allowed_transitions

    @property
    def display_name(self) -> str:
        """Return human-readable status label."""
        labels = {
            "pending_commercial_validation": "En attente validation commerciale",
            "commercial_validated": "Validé par le commercial",
            "collecting_documents": "Collecte de documents",
            "compliance_blocked": "Bloqué (conformité)",
            "configuring_contract": "Configuration du contrat",
            "draft_generated": "Brouillon généré",
            "draft_sent_to_partner": "Envoyé au partenaire",
            "partner_approved": "Approuvé par le partenaire",
            "partner_requested_changes": "Modifications demandées",
            "sent_for_signature": "Envoyé pour signature",
            "signed": "Signé",
            "archived": "Archivé",
            "redirected_payfit": "Redirigé vers PayFit",
            "cancelled": "Annulé",
        }
        return labels.get(self.value, self.value)
