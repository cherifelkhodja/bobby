"""
SQLAlchemy implementation of the Unit of Work pattern.

Provides transactional guarantees for database operations.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.unit_of_work import AbstractUnitOfWork
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    InvitationRepository,
    OpportunityRepository,
    UserRepository,
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy-based Unit of Work implementation.

    Manages a database session and provides access to repositories.
    All repository operations within a unit of work share the same session,
    ensuring transactional consistency.

    Example:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            user.is_active = False
            await uow.users.save(user)
            await uow.commit()
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Unit of Work with a session.

        Args:
            session: SQLAlchemy async session to use for all operations
        """
        self._session = session
        self._committed = False

        # Initialize repositories with the shared session
        self.users = UserRepository(session)
        self.cooptations = CooptationRepository(session)
        self.invitations = InvitationRepository(session)
        self.opportunities = OpportunityRepository(session)
        self.candidates = CandidateRepository(session)

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        """Enter the context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager.

        If an exception occurred, rollback. Otherwise, do nothing
        (explicit commit is required).
        """
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            # Auto-rollback if not explicitly committed
            await self.rollback()

    async def commit(self) -> None:
        """
        Commit the current transaction.

        All changes made through repositories will be persisted.
        """
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        All changes made through repositories will be discarded.
        """
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        """Get the underlying session (for advanced use cases)."""
        return self._session


class AutoCommitUnitOfWork(SqlAlchemyUnitOfWork):
    """
    Unit of Work that automatically commits on successful exit.

    Use this when you want automatic commit behavior:
    - If no exception occurs, changes are committed
    - If an exception occurs, changes are rolled back

    Example:
        async with AutoCommitUnitOfWork(session) as uow:
            await uow.users.save(user)
            # Auto-commits here if no exception
    """

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager with auto-commit behavior.

        Commits if no exception, rolls back if exception occurred.
        """
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()


# Factory function for creating unit of work instances
def create_unit_of_work(session: AsyncSession, auto_commit: bool = False):
    """
    Factory function to create a Unit of Work.

    Args:
        session: SQLAlchemy async session
        auto_commit: If True, auto-commit on successful exit

    Returns:
        A Unit of Work instance
    """
    if auto_commit:
        return AutoCommitUnitOfWork(session)
    return SqlAlchemyUnitOfWork(session)
