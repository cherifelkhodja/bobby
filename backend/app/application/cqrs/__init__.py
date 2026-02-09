"""
CQRS (Command Query Responsibility Segregation) infrastructure.

Separates read operations (queries) from write operations (commands)
for better scalability and maintainability.
"""

from .base import (
    Command,
    CommandBus,
    CommandHandler,
    Query,
    QueryBus,
    QueryHandler,
)
from .handlers import (
    command_bus,
    query_bus,
    register_command_handler,
    register_query_handler,
)

__all__ = [
    # Base classes
    "Command",
    "Query",
    "CommandHandler",
    "QueryHandler",
    "CommandBus",
    "QueryBus",
    # Global instances
    "command_bus",
    "query_bus",
    "register_command_handler",
    "register_query_handler",
]
