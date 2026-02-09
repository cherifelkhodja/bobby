"""
Domain Events implementation.

Domain Events are used to communicate between different parts of the application
in a loosely coupled way. When something significant happens in the domain,
an event is raised and handlers react to it.

Example usage:
    # Define an event
    class UserRegisteredEvent(DomainEvent):
        user_id: UUID
        email: str

    # Register a handler
    @event_bus.subscribe(UserRegisteredEvent)
    async def send_welcome_email(event: UserRegisteredEvent):
        await email_service.send_welcome(event.email)

    # Raise an event
    await event_bus.publish(UserRegisteredEvent(user_id=user.id, email=user.email))
"""

from .base import DomainEvent, EventBus, event_bus
from .cooptation_events import (
    CooptationAcceptedEvent,
    CooptationCreatedEvent,
    CooptationRejectedEvent,
    CooptationStatusChangedEvent,
)
from .invitation_events import (
    InvitationAcceptedEvent,
    InvitationCreatedEvent,
    InvitationExpiredEvent,
    InvitationResentEvent,
)
from .user_events import (
    PasswordResetCompletedEvent,
    PasswordResetRequestedEvent,
    UserDeactivatedEvent,
    UserRegisteredEvent,
    UserRoleChangedEvent,
    UserVerifiedEvent,
)

__all__ = [
    # Base
    "DomainEvent",
    "EventBus",
    "event_bus",
    # User events
    "UserRegisteredEvent",
    "UserVerifiedEvent",
    "UserDeactivatedEvent",
    "UserRoleChangedEvent",
    "PasswordResetRequestedEvent",
    "PasswordResetCompletedEvent",
    # Cooptation events
    "CooptationCreatedEvent",
    "CooptationStatusChangedEvent",
    "CooptationAcceptedEvent",
    "CooptationRejectedEvent",
    # Invitation events
    "InvitationCreatedEvent",
    "InvitationAcceptedEvent",
    "InvitationExpiredEvent",
    "InvitationResentEvent",
]
