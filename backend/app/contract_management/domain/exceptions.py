"""Contract management domain exceptions."""

from app.domain.exceptions import DomainError


class ContractRequestNotFoundError(DomainError):
    """Raised when a contract request is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Demande de contrat non trouvée : {identifier}")


class InvalidContractStatusError(DomainError):
    """Raised when a contract request status transition is invalid."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Transition de statut invalide : {current} → {target}"
        )


class ComplianceBlockError(DomainError):
    """Raised when compliance check blocks contract generation."""

    def __init__(self, third_party_id: str, reason: str) -> None:
        super().__init__(
            f"Blocage conformité pour le tiers {third_party_id} : {reason}"
        )


class WebhookDuplicateError(DomainError):
    """Raised when a duplicate webhook event is received."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Événement webhook déjà traité : {event_id}")


class ContractNotFoundError(DomainError):
    """Raised when a contract is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Contrat non trouvé : {identifier}")
