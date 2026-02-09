"""Database infrastructure - SQLAlchemy models and repositories."""

from app.infrastructure.database.connection import (
    async_session_factory,
    engine,
    get_async_session,
)
from app.infrastructure.database.models import (
    Base,
    CandidateModel,
    CooptationModel,
    OpportunityModel,
    UserModel,
)
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    OpportunityRepository,
    UserRepository,
)

__all__ = [
    # Connection
    "engine",
    "get_async_session",
    "async_session_factory",
    # Models
    "Base",
    "UserModel",
    "CandidateModel",
    "OpportunityModel",
    "CooptationModel",
    # Repositories
    "UserRepository",
    "OpportunityRepository",
    "CooptationRepository",
    "CandidateRepository",
]
