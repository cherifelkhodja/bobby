"""Vigilance domain exceptions."""

from app.domain.exceptions import DomainError


class DocumentNotFoundError(DomainError):
    """Raised when a vigilance document is not found."""

    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document non trouvé : {document_id}")


class DocumentNotAllowedError(DomainError):
    """Raised when a document type is forbidden (RGPD)."""

    def __init__(self, document_type: str) -> None:
        super().__init__(
            f"Type de document interdit (RGPD) : {document_type}"
        )


class InvalidDocumentTransitionError(DomainError):
    """Raised when a document status transition is invalid."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Transition invalide : {current} → {target}"
        )


class InvalidDocumentTypeError(DomainError):
    """Raised when an unknown document type is provided."""

    def __init__(self, document_type: str) -> None:
        super().__init__(f"Type de document inconnu : {document_type}")


class ComplianceBlockError(DomainError):
    """Raised when a compliance check blocks an operation."""

    def __init__(self, third_party_id: str, reason: str) -> None:
        super().__init__(
            f"Blocage conformité pour le tiers {third_party_id} : {reason}"
        )
