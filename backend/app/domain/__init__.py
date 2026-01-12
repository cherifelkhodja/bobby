"""Domain layer - business entities, value objects, and ports."""

from app.domain.entities import Candidate, Cooptation, Opportunity, User
from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    CooptationNotFoundError,
    DomainError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPhoneError,
    InvalidTokenError,
    OpportunityNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserNotVerifiedError,
)
from app.domain.value_objects import CooptationStatus, Email, Phone, UserRole

__all__ = [
    # Entities
    "Candidate",
    "Cooptation",
    "Opportunity",
    "User",
    # Value Objects
    "CooptationStatus",
    "Email",
    "Phone",
    "UserRole",
    # Exceptions
    "CandidateAlreadyExistsError",
    "CooptationNotFoundError",
    "DomainError",
    "InvalidCredentialsError",
    "InvalidEmailError",
    "InvalidPhoneError",
    "InvalidTokenError",
    "OpportunityNotFoundError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "UserNotVerifiedError",
]
