"""Domain entities - core business objects."""

from app.domain.entities.business_lead import BusinessLead, BusinessLeadStatus
from app.domain.entities.candidate import Candidate
from app.domain.entities.cooptation import Cooptation
from app.domain.entities.cv_template import CvTemplate
from app.domain.entities.cv_transformation_log import CvTransformationLog
from app.domain.entities.invitation import Invitation
from app.domain.entities.job_application import (
    ApplicationStatus,
    JobApplication,
    MatchingResult,
    StatusChange,
)
from app.domain.entities.job_posting import (
    ContractType,
    ExperienceLevel,
    JobPosting,
    JobPostingStatus,
    RemotePolicy,
)
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.user import User

__all__ = [
    "ApplicationStatus",
    "BusinessLead",
    "BusinessLeadStatus",
    "Candidate",
    "ContractType",
    "Cooptation",
    "CvTemplate",
    "CvTransformationLog",
    "ExperienceLevel",
    "Invitation",
    "JobApplication",
    "JobPosting",
    "JobPostingStatus",
    "MatchingResult",
    "Opportunity",
    "RemotePolicy",
    "StatusChange",
    "User",
]
