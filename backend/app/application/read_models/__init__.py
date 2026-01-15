"""Read models for UI (CQRS light)."""

from app.application.read_models.cooptation import (
    CooptationReadModel,
    CooptationStatsReadModel,
    CooptationListReadModel,
)
from app.application.read_models.hr import (
    ApplicationSubmissionResultReadModel,
    JobApplicationListReadModel,
    JobApplicationReadModel,
    JobPostingListReadModel,
    JobPostingPublicReadModel,
    JobPostingReadModel,
    MatchingDetailsReadModel,
    OpportunityForHRReadModel,
    OpportunityListForHRReadModel,
    StatusChangeReadModel,
)
from app.application.read_models.opportunity import (
    OpportunityReadModel,
    OpportunityListReadModel,
)
from app.application.read_models.user import UserReadModel

__all__ = [
    "ApplicationSubmissionResultReadModel",
    "CooptationReadModel",
    "CooptationStatsReadModel",
    "CooptationListReadModel",
    "JobApplicationListReadModel",
    "JobApplicationReadModel",
    "JobPostingListReadModel",
    "JobPostingPublicReadModel",
    "JobPostingReadModel",
    "MatchingDetailsReadModel",
    "OpportunityForHRReadModel",
    "OpportunityListForHRReadModel",
    "OpportunityReadModel",
    "OpportunityListReadModel",
    "StatusChangeReadModel",
    "UserReadModel",
]
