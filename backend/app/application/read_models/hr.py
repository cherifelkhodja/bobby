"""HR feature read models for job postings and applications."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpportunityForHRReadModel(BaseModel):
    """Opportunity read model for HR dashboard (with job posting status).

    Now fetched directly from BoondManager API where user is HR manager.
    """

    model_config = ConfigDict(frozen=True)

    id: str  # Boond opportunity ID
    title: str
    reference: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # Manager info
    manager_name: Optional[str] = None
    hr_manager_name: Optional[str] = None
    # State info from Boond
    state: Optional[int] = None
    state_name: Optional[str] = None
    state_color: Optional[str] = None
    # Job posting info (from local database)
    has_job_posting: bool = False
    job_posting_id: Optional[str] = None
    job_posting_status: Optional[str] = None
    job_posting_status_display: Optional[str] = None
    applications_count: int = 0
    new_applications_count: int = 0


class OpportunityListForHRReadModel(BaseModel):
    """Paginated opportunity list for HR."""

    model_config = ConfigDict(frozen=True)

    items: list[OpportunityForHRReadModel]
    total: int
    page: int
    page_size: int


class MatchingDetailsReadModel(BaseModel):
    """Matching details read model."""

    model_config = ConfigDict(frozen=True)

    score: int
    strengths: list[str]
    gaps: list[str]
    summary: str


class JobPostingReadModel(BaseModel):
    """Job posting read model."""

    model_config = ConfigDict(frozen=True)

    id: str
    opportunity_id: str
    opportunity_title: Optional[str] = None
    opportunity_reference: Optional[str] = None
    client_name: Optional[str] = None
    title: str
    description: str
    qualifications: str
    location_country: str
    location_region: Optional[str] = None
    location_postal_code: Optional[str] = None
    location_city: Optional[str] = None
    location_key: Optional[str] = None  # Turnover-IT location key
    contract_types: list[str]
    skills: list[str]
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = None
    salary_min_annual: Optional[float] = None
    salary_max_annual: Optional[float] = None
    salary_min_daily: Optional[float] = None
    salary_max_daily: Optional[float] = None
    employer_overview: Optional[str] = None
    status: str
    status_display: str
    turnoverit_reference: Optional[str] = None
    turnoverit_public_url: Optional[str] = None
    application_token: str
    application_url: Optional[str] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    # Stats
    applications_total: int = 0
    applications_new: int = 0


class JobPostingListReadModel(BaseModel):
    """Paginated job posting list."""

    model_config = ConfigDict(frozen=True)

    items: list[JobPostingReadModel]
    total: int
    page: int
    page_size: int


class JobPostingPublicReadModel(BaseModel):
    """Job posting public read model (for public application form)."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    qualifications: str
    location_country: str
    location_region: Optional[str] = None
    location_city: Optional[str] = None
    contract_types: list[str]
    skills: list[str]
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = None
    salary_min_daily: Optional[float] = None
    salary_max_daily: Optional[float] = None
    employer_overview: Optional[str] = None


class StatusChangeReadModel(BaseModel):
    """Status change history item."""

    model_config = ConfigDict(frozen=True)

    from_status: str
    to_status: str
    changed_at: datetime
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    comment: Optional[str] = None


class JobApplicationReadModel(BaseModel):
    """Job application read model."""

    model_config = ConfigDict(frozen=True)

    id: str
    job_posting_id: str
    job_posting_title: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    job_title: str
    # New fields
    availability: str
    availability_display: str
    employment_status: str
    employment_status_display: str
    english_level: str
    english_level_display: str
    tjm_current: Optional[float] = None
    tjm_desired: Optional[float] = None
    salary_current: Optional[float] = None
    salary_desired: Optional[float] = None
    tjm_range: str
    salary_range: str
    # Legacy fields (kept for backward compatibility)
    tjm_min: Optional[float] = None
    tjm_max: Optional[float] = None
    availability_date: Optional[date] = None
    cv_s3_key: str
    cv_filename: str
    cv_download_url: Optional[str] = None
    matching_score: Optional[int] = None
    matching_details: Optional[MatchingDetailsReadModel] = None
    status: str
    status_display: str
    status_history: list[StatusChangeReadModel] = []
    notes: Optional[str] = None
    boond_candidate_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobApplicationListReadModel(BaseModel):
    """Paginated job application list."""

    model_config = ConfigDict(frozen=True)

    items: list[JobApplicationReadModel]
    total: int
    page: int
    page_size: int
    stats: dict[str, int] = {}


class ApplicationSubmissionResultReadModel(BaseModel):
    """Result of application submission."""

    model_config = ConfigDict(frozen=True)

    success: bool
    application_id: str
    message: str
