"""Read models for UI (CQRS light)."""

from app.application.read_models.cooptation import (
    CooptationListReadModel,
    CooptationReadModel,
    CooptationStatsReadModel,
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
    OpportunityListReadModel,
    OpportunityReadModel,
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
