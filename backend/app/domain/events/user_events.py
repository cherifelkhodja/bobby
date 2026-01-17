"""
User-related domain events.
"""

from typing import Optional
from uuid import UUID

from pydantic import Field

from ..value_objects import UserRole
from .base import DomainEvent


class UserRegisteredEvent(DomainEvent):
    """Event raised when a new user registers."""

    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    invited_by: Optional[UUID] = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserVerifiedEvent(DomainEvent):
    """Event raised when a user verifies their email."""

    user_id: UUID
    email: str

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserDeactivatedEvent(DomainEvent):
    """Event raised when a user account is deactivated."""

    user_id: UUID
    email: str
    deactivated_by: UUID
    reason: Optional[str] = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserActivatedEvent(DomainEvent):
    """Event raised when a user account is activated."""

    user_id: UUID
    email: str
    activated_by: UUID

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserRoleChangedEvent(DomainEvent):
    """Event raised when a user's role is changed."""

    user_id: UUID
    email: str
    old_role: UserRole
    new_role: UserRole
    changed_by: UUID

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserDeletedEvent(DomainEvent):
    """Event raised when a user account is deleted."""

    user_id: UUID
    email: str
    deleted_by: UUID

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class PasswordResetRequestedEvent(DomainEvent):
    """Event raised when a password reset is requested."""

    user_id: UUID
    email: str
    token_expires_at: str  # ISO format datetime string

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class PasswordResetCompletedEvent(DomainEvent):
    """Event raised when a password reset is completed."""

    user_id: UUID
    email: str

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserLoginEvent(DomainEvent):
    """Event raised when a user logs in."""

    user_id: UUID
    email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)


class UserLogoutEvent(DomainEvent):
    """Event raised when a user logs out."""

    user_id: UUID
    email: str

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("user_id"), **data)
