"""Database infrastructure - SQLAlchemy models and repositories."""

from app.infrastructure.database.connection import (
    engine,
    get_async_session,
    async_session_factory,
)
from app.infrastructure.database.models import (
    Base,
    UserModel,
    CandidateModel,
    OpportunityModel,
    CooptationModel,
)
from app.infrastructure.database.repositories import (
    UserRepository,
    OpportunityRepository,
    CooptationRepository,
    CandidateRepository,
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
