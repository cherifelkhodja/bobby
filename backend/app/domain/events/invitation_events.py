"""
Invitation-related domain events.
"""

from uuid import UUID

from ..value_objects import UserRole
from .base import DomainEvent


class InvitationCreatedEvent(DomainEvent):
    """Event raised when an invitation is created."""

    invitation_id: UUID
    email: str
    role: UserRole
    invited_by: UUID
    expires_at: str  # ISO format datetime
    boond_resource_id: str | None = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)


class InvitationAcceptedEvent(DomainEvent):
    """Event raised when an invitation is accepted."""

    invitation_id: UUID
    email: str
    user_id: UUID  # The newly created user
    accepted_at: str  # ISO format datetime

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)


class InvitationExpiredEvent(DomainEvent):
    """Event raised when an invitation expires without being accepted."""

    invitation_id: UUID
    email: str
    expired_at: str  # ISO format datetime

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)


class InvitationResentEvent(DomainEvent):
    """Event raised when an invitation is resent."""

    invitation_id: UUID
    email: str
    resent_by: UUID
    new_expires_at: str  # ISO format datetime
    resend_count: int

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)


class InvitationCancelledEvent(DomainEvent):
    """Event raised when an invitation is cancelled."""

    invitation_id: UUID
    email: str
    cancelled_by: UUID
    reason: str | None = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)


class InvitationDeletedEvent(DomainEvent):
    """Event raised when an invitation is deleted."""

    invitation_id: UUID
    email: str
    deleted_by: UUID

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("invitation_id"), **data)
