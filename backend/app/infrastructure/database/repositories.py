"""SQLAlchemy repository implementations.

This module re-exports all repositories from the modular structure
for backward compatibility. New code should import directly from
app.infrastructure.database.repositories package.
"""

# Re-export all repositories from the modular structure
from app.infrastructure.database.repositories import (
    BaseRepository,
    BusinessLeadRepository,
    CandidateRepository,
    CooptationRepository,
    CvTemplateRepository,
    CvTransformationLogRepository,
    InvitationRepository,
    JobApplicationRepository,
    JobPostingRepository,
    OpportunityRepository,
    PublishedOpportunityRepository,
    UserRepository,
)

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
