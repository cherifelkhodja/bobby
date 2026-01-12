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
