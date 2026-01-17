"""
Base classes for Domain Events.

Provides the foundation for event-driven architecture in the domain layer.
"""

from abc import ABC
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Type, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel, ABC):
    """
    Base class for all domain events.

    Domain events represent something significant that happened in the domain.
    They are immutable and contain all the information needed to describe
    what happened.

    Attributes:
        event_id: Unique identifier for this event instance
        event_type: Type name of the event (auto-populated)
        occurred_at: When the event occurred
        aggregate_id: ID of the aggregate that raised the event (optional)
        metadata: Additional metadata about the event
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(default="")
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    aggregate_id: UUID | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-set event_type from class name
        if not self.event_type:
            object.__setattr__(self, "event_type", self.__class__.__name__)

    class Config:
        frozen = True  # Events are immutable


T = TypeVar("T", bound=DomainEvent)
EventHandler = Callable[[T], Coroutine[Any, Any, None]]


class EventBus:
    """
    Simple in-memory event bus for publishing and subscribing to domain events.

    This implementation is suitable for single-process applications.
    For distributed systems, consider using a message broker like Redis, RabbitMQ, or Kafka.

    Example:
        bus = EventBus()

        @bus.subscribe(UserRegisteredEvent)
        async def handle_user_registered(event: UserRegisteredEvent):
            print(f"User {event.email} registered!")

        await bus.publish(UserRegisteredEvent(email="user@example.com"))
    """

    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._middleware: List[Callable[[DomainEvent], Coroutine[Any, Any, None]]] = []

    def subscribe(
        self, event_type: Type[T]
    ) -> Callable[[EventHandler[T]], EventHandler[T]]:
        """
        Decorator to subscribe a handler to an event type.

        Args:
            event_type: The type of event to handle

        Returns:
            Decorator function

        Example:
            @event_bus.subscribe(UserRegisteredEvent)
            async def handle_user_registered(event: UserRegisteredEvent):
                pass
        """
        def decorator(handler: EventHandler[T]) -> EventHandler[T]:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            return handler
        return decorator

    def register_handler(
        self, event_type: Type[T], handler: EventHandler[T]
    ) -> None:
        """
        Register a handler for an event type (non-decorator version).

        Args:
            event_type: The type of event to handle
            handler: The handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister_handler(
        self, event_type: Type[T], handler: EventHandler[T]
    ) -> bool:
        """
        Unregister a handler for an event type.

        Args:
            event_type: The type of event
            handler: The handler to remove

        Returns:
            True if the handler was found and removed
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    def add_middleware(
        self, middleware: Callable[[DomainEvent], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Add middleware that runs before all event handlers.
        Useful for logging, metrics, etc.

        Args:
            middleware: Async function that receives the event
        """
        self._middleware.append(middleware)

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.

        Args:
            event: The event to publish

        Note:
            Handlers are called in the order they were registered.
            Errors in handlers are logged but don't stop other handlers.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Run middleware first
        for middleware in self._middleware:
            try:
                await middleware(event)
            except Exception as e:
                logger.error(f"Middleware error for {event.event_type}: {e}")

        # Get handlers for this event type
        handlers = self._handlers.get(type(event), [])

        if not handlers:
            logger.debug(f"No handlers registered for {event.event_type}")
            return

        # Call each handler
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed for {event.event_type}: {e}"
                )

    async def publish_all(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple events in order.

        Args:
            events: List of events to publish
        """
        for event in events:
            await self.publish(event)

    def clear_handlers(self, event_type: Type[DomainEvent] | None = None) -> None:
        """
        Clear all handlers, optionally for a specific event type.

        Args:
            event_type: If provided, only clear handlers for this type
        """
        if event_type:
            self._handlers.pop(event_type, None)
        else:
            self._handlers.clear()


# Global event bus instance
event_bus = EventBus()
