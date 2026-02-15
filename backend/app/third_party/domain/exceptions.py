"""Third party domain exceptions."""

from app.domain.exceptions import DomainError


class ThirdPartyNotFoundError(DomainError):
    """Raised when a third party is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = f"Tiers non trouvé: {identifier}" if identifier else "Tiers non trouvé"
        super().__init__(message)


class InvalidSirenError(DomainError):
    """Raised when a SIREN number is invalid."""

    def __init__(self, siren: str = "") -> None:
        message = f"Numéro SIREN invalide: {siren}" if siren else "Numéro SIREN invalide"
        super().__init__(message)


class MagicLinkExpiredError(DomainError):
    """Raised when a magic link has expired."""

    def __init__(self) -> None:
        super().__init__("Ce lien a expiré")


class MagicLinkRevokedError(DomainError):
    """Raised when a magic link has been revoked."""

    def __init__(self) -> None:
        super().__init__("Ce lien a été révoqué")


class MagicLinkNotFoundError(DomainError):
    """Raised when a magic link token is not found."""

    def __init__(self) -> None:
        super().__init__("Lien invalide ou non trouvé")
