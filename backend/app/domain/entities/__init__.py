"""Domain entities - core business objects."""

from app.domain.entities.candidate import Candidate
from app.domain.entities.cooptation import Cooptation
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.user import User

__all__ = [
    "Candidate",
    "Cooptation",
    "Opportunity",
    "User",
]
