"""
CQRS handler registry and example handlers.

Provides global command and query buses with registration utilities.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Type
from uuid import UUID

from .base import (
    Command,
    CommandBus,
    CommandHandler,
    Query,
    QueryBus,
    QueryHandler,
)

# Global bus instances
command_bus = CommandBus()
query_bus = QueryBus()


def register_command_handler(
    command_type: Type[Command],
) -> Callable[[Type[CommandHandler]], Type[CommandHandler]]:
    """
    Decorator to register a command handler.

    Example:
        @register_command_handler(CreateUserCommand)
        class CreateUserCommandHandler(CommandHandler[CreateUserCommand]):
            async def handle(self, command: CreateUserCommand) -> UUID:
                ...
    """

    def decorator(handler_class: Type[CommandHandler]) -> Type[CommandHandler]:
        # Create instance and register
        # Note: In production, you'd use dependency injection here
        handler = handler_class()
        command_bus.register(command_type, handler)
        return handler_class

    return decorator


def register_query_handler(
    query_type: Type[Query],
) -> Callable[[Type[QueryHandler]], Type[QueryHandler]]:
    """
    Decorator to register a query handler.

    Example:
        @register_query_handler(GetUserByIdQuery)
        class GetUserByIdQueryHandler(QueryHandler[GetUserByIdQuery, UserDTO]):
            async def handle(self, query: GetUserByIdQuery) -> UserDTO:
                ...
    """

    def decorator(handler_class: Type[QueryHandler]) -> Type[QueryHandler]:
        handler = handler_class()
        query_bus.register(query_type, handler)
        return handler_class

    return decorator


# =============================================================================
# Example Commands and Queries
# =============================================================================


@dataclass(frozen=True)
class CreateCooptationCommand(Command):
    """Command to create a new cooptation."""

    opportunity_id: UUID
    coopter_id: UUID
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    candidate_linkedin: Optional[str] = None
    candidate_cv_url: Optional[str] = None
    candidate_daily_rate: Optional[int] = None
    comment: Optional[str] = None


@dataclass(frozen=True)
class UpdateCooptationStatusCommand(Command):
    """Command to update a cooptation's status."""

    cooptation_id: UUID
    new_status: str
    updated_by: UUID
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class GetCooptationByIdQuery(Query):
    """Query to get a cooptation by ID."""

    cooptation_id: UUID


@dataclass(frozen=True)
class ListUserCooptationsQuery(Query):
    """Query to list cooptations for a user."""

    user_id: UUID
    page: int = 1
    page_size: int = 20
    status: Optional[str] = None


@dataclass(frozen=True)
class GetCooptationStatsQuery(Query):
    """Query to get cooptation statistics."""

    user_id: Optional[UUID] = None  # None = all users (admin only)


# =============================================================================
# Example DTOs (Data Transfer Objects)
# =============================================================================


@dataclass
class CooptationDTO:
    """Data transfer object for cooptation."""

    id: UUID
    opportunity_id: UUID
    opportunity_title: str
    coopter_id: UUID
    coopter_name: str
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str]
    status: str
    status_display: str
    submitted_at: str
    rejection_reason: Optional[str] = None


@dataclass
class CooptationStatsDTO:
    """Data transfer object for cooptation statistics."""

    total: int
    pending: int
    in_review: int
    accepted: int
    rejected: int
    by_status: dict[str, int]


@dataclass
class PaginatedResult:
    """Generic paginated result."""

    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
