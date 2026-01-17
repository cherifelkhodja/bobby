"""
Unit of Work pattern implementation.

The Unit of Work pattern maintains a list of objects affected by a business transaction
and coordinates writing out changes and resolution of concurrency problems.

It ensures that all operations in a transaction either succeed or fail together,
maintaining data consistency.

Example usage:
    async with unit_of_work:
        user = await unit_of_work.users.get_by_id(user_id)
        user.deactivate()
        await unit_of_work.users.save(user)
        await unit_of_work.commit()

    # Or with automatic commit on success:
    async with unit_of_work:
        await unit_of_work.users.save(user)
        # auto-commits if no exception
"""

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from .ports.repositories import (
    CandidateRepositoryPort,
    CooptationRepositoryPort,
    InvitationRepositoryPort,
    OpportunityRepositoryPort,
    UserRepositoryPort,
)


@runtime_checkable
class UnitOfWorkPort(Protocol):
    """
    Protocol defining the Unit of Work interface.

    The Unit of Work provides access to repositories and manages
    the transaction lifecycle (commit/rollback).
    """

    # Repository accessors
    users: UserRepositoryPort
    cooptations: CooptationRepositoryPort
    invitations: InvitationRepositoryPort
    opportunities: OpportunityRepositoryPort
    candidates: CandidateRepositoryPort

    async def commit(self) -> None:
        """Commit the transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...

    async def __aenter__(self) -> "UnitOfWorkPort":
        """Enter the context manager."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        ...


class AbstractUnitOfWork(ABC):
    """
    Abstract base class for Unit of Work implementations.

    Provides the structure and lifecycle management for units of work.
    Concrete implementations should provide actual repository instances
    and database session management.
    """

    users: UserRepositoryPort
    cooptations: CooptationRepositoryPort
    invitations: InvitationRepositoryPort
    opportunities: OpportunityRepositoryPort
    candidates: CandidateRepositoryPort

    async def __aenter__(self) -> "AbstractUnitOfWork":
        """Enter the context manager and start a new transaction."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager.

        If an exception occurred, rollback the transaction.
        Otherwise, the transaction should be explicitly committed by the caller.
        """
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """
        Commit the current transaction.

        This persists all changes made through the repositories
        during this unit of work.
        """
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        This discards all changes made through the repositories
        during this unit of work.
        """
        raise NotImplementedError

    async def collect_new_events(self) -> list:
        """
        Collect domain events from all entities managed by this unit of work.

        Override this method to gather events from aggregate roots
        for publishing after commit.
        """
        return []
