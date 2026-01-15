"""HR feature read models for job postings and applications."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpportunityForHRReadModel(BaseModel):
    """Opportunity read model for HR dashboard (with job posting status)."""

    model_config = ConfigDict(frozen=True)

    id: str
    external_id: str
    title: str
    reference: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = []
    location: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manager_name: Optional[str] = None
    synced_at: datetime
    # Job posting info
    has_job_posting: bool = False
    job_posting_id: Optional[str] = None
    job_posting_status: Optional[str] = None
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
    tjm_min: float
    tjm_max: float
    tjm_range: str
    availability_date: date
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
