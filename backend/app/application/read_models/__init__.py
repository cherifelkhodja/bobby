"""Read models for UI (CQRS light)."""

from app.application.read_models.cooptation import (
    CooptationReadModel,
    CooptationStatsReadModel,
    CooptationListReadModel,
)
from app.application.read_models.opportunity import (
    OpportunityReadModel,
    OpportunityListReadModel,
)
from app.application.read_models.user import UserReadModel

__all__ = [
    "CooptationReadModel",
    "CooptationStatsReadModel",
    "CooptationListReadModel",
    "OpportunityReadModel",
    "OpportunityListReadModel",
    "UserReadModel",
]
