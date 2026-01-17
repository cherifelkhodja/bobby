"""Domain exceptions - pure business logic errors without HTTP coupling."""


class DomainError(Exception):
    """Base class for domain exceptions."""

    def __init__(self, message: str = "A domain error occurred") -> None:
        self.message = message
        super().__init__(self.message)


# User domain errors
class UserNotFoundError(DomainError):
    """Raised when a user is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = f"User not found: {identifier}" if identifier else "User not found"
        super().__init__(message)


class UserAlreadyExistsError(DomainError):
    """Raised when trying to create a user that already exists."""

    def __init__(self, email: str = "") -> None:
        message = f"User already exists: {email}" if email else "User already exists"
        super().__init__(message)


class UserNotVerifiedError(DomainError):
    """Raised when user email is not verified."""

    def __init__(self) -> None:
        super().__init__("User email is not verified")


class InvalidCredentialsError(DomainError):
    """Raised when credentials are invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InvalidTokenError(DomainError):
    """Raised when a token is invalid or expired."""

    def __init__(self, reason: str = "") -> None:
        message = f"Invalid token: {reason}" if reason else "Invalid or expired token"
        super().__init__(message)


# Candidate domain errors
class CandidateAlreadyExistsError(DomainError):
    """Raised when a candidate already exists."""

    def __init__(self, email: str = "") -> None:
        message = f"Candidate already exists: {email}" if email else "Candidate already exists"
        super().__init__(message)


# Opportunity domain errors
class OpportunityNotFoundError(DomainError):
    """Raised when an opportunity is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = f"Opportunity not found: {identifier}" if identifier else "Opportunity not found"
        super().__init__(message)


# Cooptation domain errors
class CooptationNotFoundError(DomainError):
    """Raised when a cooptation is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = (
            f"Cooptation not found: {identifier}" if identifier else "Cooptation not found"
        )
        super().__init__(message)


# Value object errors
class InvalidEmailError(DomainError):
    """Raised when an email is invalid."""

    def __init__(self, email: str = "") -> None:
        message = f"Invalid email format: {email}" if email else "Invalid email format"
        super().__init__(message)


class InvalidPhoneError(DomainError):
    """Raised when a phone number is invalid."""

    def __init__(self, phone: str = "") -> None:
        message = f"Invalid phone format: {phone}" if phone else "Invalid phone format"
        super().__init__(message)


# Job posting domain errors
class JobPostingNotFoundError(DomainError):
    """Raised when a job posting is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = (
            f"Offre d'emploi non trouvée: {identifier}"
            if identifier
            else "Offre d'emploi non trouvée"
        )
        super().__init__(message)


class InvalidJobPostingError(DomainError):
    """Raised when job posting data is invalid."""

    def __init__(self, message: str = "") -> None:
        error_msg = message if message else "Données d'offre d'emploi invalides"
        super().__init__(error_msg)


class JobPostingAlreadyPublishedError(DomainError):
    """Raised when trying to publish an already published job posting."""

    def __init__(self) -> None:
        super().__init__("Cette offre est déjà publiée")


class JobPostingClosedError(DomainError):
    """Raised when trying to modify a closed job posting."""

    def __init__(self) -> None:
        super().__init__("Cette offre est fermée et ne peut pas être modifiée")


class JobPostingValidationError(DomainError):
    """Raised when job posting validation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = f"Erreurs de validation: {'; '.join(errors)}"
        super().__init__(message)


# Job application domain errors
class JobApplicationNotFoundError(DomainError):
    """Raised when a job application is not found."""

    def __init__(self, identifier: str = "") -> None:
        message = (
            f"Candidature non trouvée: {identifier}"
            if identifier
            else "Candidature non trouvée"
        )
        super().__init__(message)


class InvalidJobApplicationError(DomainError):
    """Raised when job application data is invalid."""

    def __init__(self, message: str = "") -> None:
        error_msg = message if message else "Données de candidature invalides"
        super().__init__(error_msg)


class InvalidStatusTransitionError(DomainError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Transition de statut invalide: {from_status} → {to_status}")


class ApplicationAlreadyInBoondError(DomainError):
    """Raised when trying to create a candidate that already exists in BoondManager."""

    def __init__(self) -> None:
        super().__init__("Ce candidat existe déjà dans BoondManager")


# External service errors
class TurnoverITError(DomainError):
    """Raised when Turnover-IT API call fails."""

    def __init__(self, message: str = "") -> None:
        error_msg = f"Erreur Turnover-IT: {message}" if message else "Erreur Turnover-IT"
        super().__init__(error_msg)


class S3StorageError(DomainError):
    """Raised when S3/MinIO storage operation fails."""

    def __init__(self, message: str = "") -> None:
        error_msg = f"Erreur de stockage: {message}" if message else "Erreur de stockage"
        super().__init__(error_msg)


class CvMatchingError(DomainError):
    """Raised when CV matching analysis fails."""

    def __init__(self, message: str = "") -> None:
        error_msg = f"Erreur d'analyse: {message}" if message else "Erreur d'analyse du CV"
        super().__init__(error_msg)
