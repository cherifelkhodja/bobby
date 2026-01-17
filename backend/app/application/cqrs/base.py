"""
CQRS base classes.

Provides the foundation for Command and Query patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

# Type variables for command and query results
TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand", bound="Command")
TQuery = TypeVar("TQuery", bound="Query")


@dataclass(frozen=True)
class Command:
    """
    Base class for commands.

    Commands represent intentions to change the system state.
    They are handled by CommandHandlers and typically don't return data.

    Example:
        @dataclass(frozen=True)
        class CreateUserCommand(Command):
            email: str
            password: str
            first_name: str
            last_name: str
    """

    pass


@dataclass(frozen=True)
class Query(Generic[TResult]):
    """
    Base class for queries.

    Queries represent requests for data and should never modify state.
    They return typed results through QueryHandlers.

    Example:
        @dataclass(frozen=True)
        class GetUserByIdQuery(Query[UserDTO]):
            user_id: UUID
    """

    pass


class CommandHandler(ABC, Generic[TCommand]):
    """
    Base class for command handlers.

    Command handlers process commands and perform state changes.
    They should not return domain data (only success/failure indicators).

    Example:
        class CreateUserCommandHandler(CommandHandler[CreateUserCommand]):
            async def handle(self, command: CreateUserCommand) -> None:
                user = User.create(
                    email=command.email,
                    password=command.password,
                    ...
                )
                await self.repository.save(user)
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> Any:
        """
        Handle a command.

        Args:
            command: The command to handle

        Returns:
            Optional result (typically None or an ID)
        """
        pass


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """
    Base class for query handlers.

    Query handlers process queries and return data without modifying state.

    Example:
        class GetUserByIdQueryHandler(QueryHandler[GetUserByIdQuery, UserDTO]):
            async def handle(self, query: GetUserByIdQuery) -> UserDTO:
                user = await self.repository.get_by_id(query.user_id)
                return UserDTO.from_entity(user)
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """
        Handle a query.

        Args:
            query: The query to handle

        Returns:
            Query result
        """
        pass


class CommandBus:
    """
    Command bus for dispatching commands to their handlers.

    The command bus routes commands to the appropriate handler
    and ensures only one handler processes each command type.

    Example:
        bus = CommandBus()
        bus.register(CreateUserCommand, CreateUserCommandHandler())

        await bus.dispatch(CreateUserCommand(
            email="user@example.com",
            password="secret",
            ...
        ))
    """

    def __init__(self):
        self._handlers: dict[type, CommandHandler] = {}

    def register(
        self,
        command_type: type[Command],
        handler: CommandHandler,
    ) -> None:
        """
        Register a handler for a command type.

        Args:
            command_type: The command class
            handler: The handler instance
        """
        self._handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        """
        Dispatch a command to its handler.

        Args:
            command: The command to dispatch

        Returns:
            Handler result

        Raises:
            ValueError: If no handler is registered for the command type
        """
        handler = self._handlers.get(type(command))
        if handler is None:
            raise ValueError(
                f"No handler registered for command type: {type(command).__name__}"
            )
        return await handler.handle(command)

    def has_handler(self, command_type: type[Command]) -> bool:
        """Check if a handler is registered for a command type."""
        return command_type in self._handlers


class QueryBus:
    """
    Query bus for dispatching queries to their handlers.

    The query bus routes queries to the appropriate handler
    and returns the query results.

    Example:
        bus = QueryBus()
        bus.register(GetUserByIdQuery, GetUserByIdQueryHandler())

        user = await bus.dispatch(GetUserByIdQuery(user_id=uuid))
    """

    def __init__(self):
        self._handlers: dict[type, QueryHandler] = {}

    def register(
        self,
        query_type: type[Query],
        handler: QueryHandler,
    ) -> None:
        """
        Register a handler for a query type.

        Args:
            query_type: The query class
            handler: The handler instance
        """
        self._handlers[query_type] = handler

    async def dispatch(self, query: Query[TResult]) -> TResult:
        """
        Dispatch a query to its handler.

        Args:
            query: The query to dispatch

        Returns:
            Query result

        Raises:
            ValueError: If no handler is registered for the query type
        """
        handler = self._handlers.get(type(query))
        if handler is None:
            raise ValueError(
                f"No handler registered for query type: {type(query).__name__}"
            )
        return await handler.handle(query)

    def has_handler(self, query_type: type[Query]) -> bool:
        """Check if a handler is registered for a query type."""
        return query_type in self._handlers
