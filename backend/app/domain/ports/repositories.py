"""Repository port interfaces."""

from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities import (
    ApplicationStatus,
    BusinessLead,
    Candidate,
    Cooptation,
    CvTemplate,
    CvTransformationLog,
    Invitation,
    JobApplication,
    JobPosting,
    JobPostingStatus,
    Opportunity,
    User,
)
from app.domain.entities.business_lead import BusinessLeadStatus
from app.domain.value_objects import CooptationStatus, UserRole


class UserRepositoryPort(Protocol):
    """Port for user persistence operations."""

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        ...

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by verification token."""
        ...

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by reset token."""
        ...

    async def save(self, user: User) -> User:
        """Save user (create or update)."""
        ...

    async def delete(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        ...

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users with pagination."""
        ...

    async def count(self) -> int:
        """Count total users."""
        ...


class OpportunityRepositoryPort(Protocol):
    """Port for opportunity persistence operations."""

    async def get_by_id(self, opportunity_id: UUID) -> Optional[Opportunity]:
        """Get opportunity by ID."""
        ...

    async def get_by_external_id(self, external_id: str) -> Optional[Opportunity]:
        """Get opportunity by external BoondManager ID."""
        ...

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """Save opportunity (create or update)."""
        ...

    async def save_many(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Save multiple opportunities."""
        ...

    async def delete(self, opportunity_id: UUID) -> bool:
        """Delete opportunity by ID."""
        ...

    async def list_active(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> list[Opportunity]:
        """List active opportunities with pagination and optional search."""
        ...

    async def count_active(self, search: Optional[str] = None) -> int:
        """Count active opportunities."""
        ...


class CooptationRepositoryPort(Protocol):
    """Port for cooptation persistence operations."""

    async def get_by_id(self, cooptation_id: UUID) -> Optional[Cooptation]:
        """Get cooptation by ID."""
        ...

    async def get_by_candidate_email_and_opportunity(
        self,
        email: str,
        opportunity_id: UUID,
    ) -> Optional[Cooptation]:
        """Check if candidate already proposed for opportunity."""
        ...

    async def save(self, cooptation: Cooptation) -> Cooptation:
        """Save cooptation (create or update)."""
        ...

    async def delete(self, cooptation_id: UUID) -> bool:
        """Delete cooptation by ID."""
        ...

    async def list_by_submitter(
        self,
        submitter_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cooptation]:
        """List cooptations by submitter."""
        ...

    async def list_by_status(
        self,
        status: CooptationStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cooptation]:
        """List cooptations by status."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CooptationStatus] = None,
    ) -> list[Cooptation]:
        """List all cooptations with optional status filter."""
        ...

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count cooptations by submitter."""
        ...

    async def count_by_status(self, status: CooptationStatus) -> int:
        """Count cooptations by status."""
        ...

    async def get_stats_by_submitter(self, submitter_id: UUID) -> dict[str, int]:
        """Get cooptation statistics for a submitter."""
        ...


class CandidateRepositoryPort(Protocol):
    """Port for candidate persistence operations."""

    async def get_by_id(self, candidate_id: UUID) -> Optional[Candidate]:
        """Get candidate by ID."""
        ...

    async def get_by_email(self, email: str) -> Optional[Candidate]:
        """Get candidate by email."""
        ...

    async def get_by_external_id(self, external_id: str) -> Optional[Candidate]:
        """Get candidate by external BoondManager ID."""
        ...

    async def save(self, candidate: Candidate) -> Candidate:
        """Save candidate (create or update)."""
        ...

    async def delete(self, candidate_id: UUID) -> bool:
        """Delete candidate by ID."""
        ...


class InvitationRepositoryPort(Protocol):
    """Port for invitation persistence operations."""

    async def get_by_id(self, invitation_id: UUID) -> Optional[Invitation]:
        """Get invitation by ID."""
        ...

    async def get_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token."""
        ...

    async def get_by_email(self, email: str) -> Optional[Invitation]:
        """Get pending invitation by email."""
        ...

    async def save(self, invitation: Invitation) -> Invitation:
        """Save invitation (create or update)."""
        ...

    async def delete(self, invitation_id: UUID) -> bool:
        """Delete invitation by ID."""
        ...

    async def list_pending(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invitation]:
        """List pending (not accepted, not expired) invitations."""
        ...

    async def count_pending(self) -> int:
        """Count pending invitations."""
        ...


class BusinessLeadRepositoryPort(Protocol):
    """Port for business lead persistence operations."""

    async def get_by_id(self, lead_id: UUID) -> Optional[BusinessLead]:
        """Get business lead by ID."""
        ...

    async def save(self, lead: BusinessLead) -> BusinessLead:
        """Save business lead (create or update)."""
        ...

    async def delete(self, lead_id: UUID) -> bool:
        """Delete business lead by ID."""
        ...

    async def list_by_submitter(
        self,
        submitter_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads by submitter."""
        ...

    async def list_by_manager(
        self,
        manager_boond_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads visible to a manager (via submitter's manager_boond_id)."""
        ...

    async def list_by_status(
        self,
        status: BusinessLeadStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads by status."""
        ...

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count business leads by submitter."""
        ...

    async def count_by_status(self, status: BusinessLeadStatus) -> int:
        """Count business leads by status."""
        ...


class CvTemplateRepositoryPort(Protocol):
    """Port for CV template persistence operations."""

    async def get_by_id(self, template_id: UUID) -> Optional[CvTemplate]:
        """Get template by ID."""
        ...

    async def get_by_name(self, name: str) -> Optional[CvTemplate]:
        """Get template by unique name."""
        ...

    async def save(self, template: CvTemplate) -> CvTemplate:
        """Save template (create or update)."""
        ...

    async def delete(self, template_id: UUID) -> bool:
        """Delete template by ID."""
        ...

    async def list_active(self) -> list[CvTemplate]:
        """List all active templates."""
        ...

    async def list_all(self) -> list[CvTemplate]:
        """List all templates (including inactive)."""
        ...


class CvTransformationLogRepositoryPort(Protocol):
    """Port for CV transformation log persistence operations."""

    async def save(self, log: CvTransformationLog) -> CvTransformationLog:
        """Save transformation log."""
        ...

    async def count_by_user(self, user_id: UUID, success_only: bool = True) -> int:
        """Count transformations by user."""
        ...

    async def get_stats_by_user(self) -> list[dict]:
        """Get transformation stats grouped by user."""
        ...

    async def get_total_count(self, success_only: bool = True) -> int:
        """Get total transformation count."""
        ...


class JobPostingRepositoryPort(Protocol):
    """Port for job posting persistence operations."""

    async def get_by_id(self, posting_id: UUID) -> Optional[JobPosting]:
        """Get job posting by ID."""
        ...

    async def get_by_token(self, token: str) -> Optional[JobPosting]:
        """Get job posting by application token."""
        ...

    async def get_by_opportunity_id(self, opportunity_id: UUID) -> Optional[JobPosting]:
        """Get job posting by linked opportunity ID."""
        ...

    async def get_by_turnoverit_reference(self, reference: str) -> Optional[JobPosting]:
        """Get job posting by Turnover-IT reference."""
        ...

    async def save(self, posting: JobPosting) -> JobPosting:
        """Save job posting (create or update)."""
        ...

    async def delete(self, posting_id: UUID) -> bool:
        """Delete job posting by ID."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[JobPostingStatus] = None,
    ) -> list[JobPosting]:
        """List all job postings with optional status filter."""
        ...

    async def list_published(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        """List published job postings."""
        ...

    async def list_by_creator(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        """List job postings created by a specific user."""
        ...

    async def count_all(self, status: Optional[JobPostingStatus] = None) -> int:
        """Count all job postings with optional status filter."""
        ...

    async def count_by_creator(self, user_id: UUID) -> int:
        """Count job postings created by a specific user."""
        ...


class JobApplicationRepositoryPort(Protocol):
    """Port for job application persistence operations."""

    async def get_by_id(self, application_id: UUID) -> Optional[JobApplication]:
        """Get job application by ID."""
        ...

    async def get_by_email_and_posting(
        self,
        email: str,
        posting_id: UUID,
    ) -> Optional[JobApplication]:
        """Get application by email and posting (to check for duplicates)."""
        ...

    async def save(self, application: JobApplication) -> JobApplication:
        """Save job application (create or update)."""
        ...

    async def delete(self, application_id: UUID) -> bool:
        """Delete job application by ID."""
        ...

    async def list_by_posting(
        self,
        posting_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
        sort_by_score: bool = True,
    ) -> list[JobApplication]:
        """List applications for a job posting with optional status filter."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
    ) -> list[JobApplication]:
        """List all applications with optional status filter."""
        ...

    async def count_by_posting(
        self,
        posting_id: UUID,
        status: Optional[ApplicationStatus] = None,
    ) -> int:
        """Count applications for a job posting with optional status filter."""
        ...

    async def count_unread_by_posting(self, posting_id: UUID) -> int:
        """Count unread applications for a job posting."""
        ...

    async def get_stats_by_posting(self, posting_id: UUID) -> dict[str, int]:
        """Get application statistics for a job posting (by status)."""
        ...
