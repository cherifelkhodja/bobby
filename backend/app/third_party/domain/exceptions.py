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

    def __init__(self, identifier: str = "") -> None:
        message = f"Ce lien a expiré: {identifier}" if identifier else "Ce lien a expiré"
        super().__init__(message)


class MagicLinkRevokedError(DomainError):
    """Raised when a magic link has been revoked."""

    def __init__(self, identifier: str = "") -> None:
        message = f"Ce lien a été révoqué: {identifier}" if identifier else "Ce lien a été révoqué"
        super().__init__(message)


class MagicLinkNotFoundError(DomainError):
    """Raised when a magic link token is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = (
            f"Lien invalide ou non trouvé: {identifier}"
            if identifier
            else "Lien invalide ou non trouvé"
        )
        super().__init__(message)
