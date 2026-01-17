"""Repository implementations for database access."""

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.repositories.business_lead_repository import (
    BusinessLeadRepository,
)
from app.infrastructure.database.repositories.candidate_repository import (
    CandidateRepository,
)
from app.infrastructure.database.repositories.cooptation_repository import (
    CooptationRepository,
)
from app.infrastructure.database.repositories.cv_template_repository import (
    CvTemplateRepository,
)
from app.infrastructure.database.repositories.cv_transformation_log_repository import (
    CvTransformationLogRepository,
)
from app.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from app.infrastructure.database.repositories.job_application_repository import (
    JobApplicationRepository,
)
from app.infrastructure.database.repositories.job_posting_repository import (
    JobPostingRepository,
)
from app.infrastructure.database.repositories.opportunity_repository import (
    OpportunityRepository,
)
from app.infrastructure.database.repositories.published_opportunity_repository import (
    PublishedOpportunityRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "BusinessLeadRepository",
    "CandidateRepository",
    "CooptationRepository",
    "CvTemplateRepository",
    "CvTransformationLogRepository",
    "InvitationRepository",
    "JobApplicationRepository",
    "JobPostingRepository",
    "OpportunityRepository",
    "PublishedOpportunityRepository",
    "UserRepository",
]
