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


class ScoresDetailsReadModel(BaseModel):
    """Detailed scoring breakdown by category."""

    model_config = ConfigDict(frozen=True)

    competences_techniques: int = 0
    experience: int = 0
    formation: int = 0
    soft_skills: int = 0


class MatchingRecommendationReadModel(BaseModel):
    """Matching recommendation read model."""

    model_config = ConfigDict(frozen=True)

    niveau: str = "faible"  # fort, moyen, faible
    action_suggeree: str = ""


class MatchingDetailsReadModel(BaseModel):
    """Enhanced matching details read model with detailed scores."""

    model_config = ConfigDict(frozen=True)

    # Legacy fields (kept for backward compatibility)
    score: int
    strengths: list[str] = []
    gaps: list[str] = []
    summary: str = ""

    # Enhanced fields
    score_global: Optional[int] = None
    scores_details: Optional[ScoresDetailsReadModel] = None
    competences_matchees: list[str] = []
    competences_manquantes: list[str] = []
    points_forts: list[str] = []
    points_vigilance: list[str] = []
    synthese: str = ""
    recommandation: Optional[MatchingRecommendationReadModel] = None


# ============== CV Quality Evaluation Models ==============

class StabilityScoreReadModel(BaseModel):
    """Mission stability score details."""

    model_config = ConfigDict(frozen=True)

    note: float
    max: int = 8
    duree_moyenne_mois: float = 0
    commentaire: str = ""


class AccountQualityScoreReadModel(BaseModel):
    """Account/employer quality score details."""

    model_config = ConfigDict(frozen=True)

    note: float
    max: int = 6
    comptes_identifies: list[str] = []
    commentaire: str = ""


class EducationScoreReadModel(BaseModel):
    """Education score details."""

    model_config = ConfigDict(frozen=True)

    note: float
    max: int = 4  # 2/4/6 depending on experience level
    formations_identifiees: list[str] = []
    commentaire: str = ""


class ContinuityScoreReadModel(BaseModel):
    """Career continuity score details."""

    model_config = ConfigDict(frozen=True)

    note: float
    max: int = 4
    trous_identifies: list[str] = []
    commentaire: str = ""


class BonusMalusReadModel(BaseModel):
    """Bonus/malus adjustments."""

    model_config = ConfigDict(frozen=True)

    valeur: float = 0
    raisons: list[str] = []


class CvQualityDetailsNotesReadModel(BaseModel):
    """Detailed notes breakdown for CV quality."""

    model_config = ConfigDict(frozen=True)

    stabilite_missions: Optional[StabilityScoreReadModel] = None
    qualite_comptes: Optional[AccountQualityScoreReadModel] = None
    parcours_scolaire: Optional[EducationScoreReadModel] = None
    continuite_parcours: Optional[ContinuityScoreReadModel] = None
    bonus_malus: Optional[BonusMalusReadModel] = None


class CvQualityReadModel(BaseModel):
    """CV quality evaluation result (/20)."""

    model_config = ConfigDict(frozen=True)

    niveau_experience: str  # JUNIOR, CONFIRME, SENIOR
    annees_experience: float = 0
    note_globale: float  # 0-20
    details_notes: Optional[CvQualityDetailsNotesReadModel] = None
    points_forts: list[str] = []
    points_faibles: list[str] = []
    synthese: str = ""
    classification: str  # EXCELLENT, BON, MOYEN, FAIBLE


class JobPostingReadModel(BaseModel):
    """Job posting read model."""

    model_config = ConfigDict(frozen=True)

    id: str
    opportunity_id: str
    boond_opportunity_id: Optional[str] = None  # Boond external ID for API calls
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
    # CV Quality evaluation (/20)
    cv_quality_score: Optional[float] = None
    cv_quality: Optional[CvQualityReadModel] = None
    # Read state (separate from status)
    is_read: bool = False
    status: str
    status_display: str
    status_history: list[StatusChangeReadModel] = []
    notes: Optional[str] = None
    boond_candidate_id: Optional[str] = None
    boond_sync_error: Optional[str] = None
    boond_synced_at: Optional[datetime] = None
    boond_sync_status: str = "not_applicable"
    civility: Optional[str] = None
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
