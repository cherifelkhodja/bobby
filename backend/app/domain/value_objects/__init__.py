"""Domain value objects - immutable domain primitives."""

from app.domain.value_objects.email import Email
from app.domain.value_objects.phone import Phone
from app.domain.value_objects.status import CooptationStatus, OpportunityStatus, UserRole

__all__ = [
    "Email",
    "Phone",
    "CooptationStatus",
    "OpportunityStatus",
    "UserRole",
]
