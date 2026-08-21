"""Contract management domain exceptions."""

from app.domain.exceptions import DomainError


class ContractRequestNotFoundError(DomainError):
    """Raised when a contract request is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Demande de contrat non trouvée : {identifier}")


class InvalidContractStatusError(DomainError):
    """Raised when a contract request status transition is invalid."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Transition de statut invalide : {current} → {target}")


class ComplianceBlockError(DomainError):
    """Raised when compliance check blocks contract generation."""

    def __init__(self, third_party_id: str, reason: str) -> None:
        super().__init__(f"Blocage conformité pour le tiers {third_party_id} : {reason}")


class WebhookDuplicateError(DomainError):
    """Raised when a duplicate webhook event is received."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Événement webhook déjà traité : {event_id}")


class ContractNotFoundError(DomainError):
    """Raised when a contract is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Contrat non trouvé : {identifier}")


class PurchaseOrderNotFoundError(DomainError):
    """Raised when a purchase order is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Bon de commande non trouvé : {identifier}")


class InvalidPurchaseOrderStatusError(DomainError):
    """Raised when a purchase order status transition is invalid."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Transition de statut invalide : {current} → {target}")


class PurchaseOrderIncompleteError(DomainError):
    """Raised when a purchase order misses fields required to be generated."""

    def __init__(self, reference: str, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"Bon de commande {reference} incomplet — il manque : {', '.join(missing)}."
        )


class FrameworkContractNotSignedError(DomainError):
    """Raised when sending a purchase order before its framework contract is signed."""

    def __init__(self, reference: str) -> None:
        super().__init__(
            f"Le contrat cadre du fournisseur n'est pas signé : le bon de commande "
            f"{reference} ne peut pas encore être envoyé en signature."
        )
