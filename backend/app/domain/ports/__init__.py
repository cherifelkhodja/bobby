"""Domain ports - interfaces for external dependencies."""

from app.domain.ports.repositories import (
    CooptationRepositoryPort,
    OpportunityRepositoryPort,
    UserRepositoryPort,
)
from app.domain.ports.services import (
    BoondServicePort,
    CacheServicePort,
    EmailServicePort,
)

__all__ = [
    "CooptationRepositoryPort",
    "OpportunityRepositoryPort",
    "UserRepositoryPort",
    "BoondServicePort",
    "CacheServicePort",
    "EmailServicePort",
]
