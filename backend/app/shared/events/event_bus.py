"""Simple in-process event bus (mediator pattern).

Allows bounded contexts to communicate through domain events
without direct coupling.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()

# Type alias for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


@dataclass
class DomainEvent:
    """Base class for domain events."""

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractRequestCreated(DomainEvent):
    """Fired when a new contract request is created."""

    event_type: str = "contract_request_created"


@dataclass
class ComplianceStatusChanged(DomainEvent):
    """Fired when a third party's compliance status changes."""

    event_type: str = "compliance_status_changed"


@dataclass
class ContractSigned(DomainEvent):
    """Fired when a contract is signed."""

    event_type: str = "contract_signed"


@dataclass
class DocumentExpired(DomainEvent):
    """Fired when a document expires."""

    event_type: str = "document_expired"


class EventBus:
    """Simple in-process event bus.

    Handlers are registered by event type and called in order
    when an event is published. Errors in handlers are logged
    but do not prevent other handlers from executing.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The event type string.
            handler: Async callable to handle the event.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("event_handler_registered", event_type=event_type)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers.

        Args:
            event: The domain event to publish.
        """
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error(
                    "event_handler_error",
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(exc),
                )

        logger.info(
            "event_published",
            event_type=event.event_type,
            handlers_count=len(handlers),
        )


# Global event bus instance
event_bus = EventBus()
