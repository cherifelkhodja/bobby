"""HR feature read models for job postings and applications."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OpportunityForHRReadModel(BaseModel):
    """Opportunity read model for HR dashboard (with job posting status).

    Now fetched directly from BoondManager API where user is HR manager.
    """

    model_config = ConfigDict(frozen=True)

    id: str  # Boond opportunity ID
    title: str
    reference: str
    client_name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    # Manager info
    manager_name: str | None = None
    hr_manager_name: str | None = None
    # State info from Boond
    state: int | None = None
    state_name: str | None = None
    state_color: str | None = None
    # Job posting info (from local database)
    has_job_posting: bool = False
    job_posting_id: str | None = None
    job_posting_status: str | None = None
    job_posting_status_display: str | None = None
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
    score_global: int | None = None
    scores_details: ScoresDetailsReadModel | None = None
    competences_matchees: list[str] = []
    competences_manquantes: list[str] = []
    points_forts: list[str] = []
    points_vigilance: list[str] = []
    synthese: str = ""
    recommandation: MatchingRecommendationReadModel | None = None


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

    stabilite_missions: StabilityScoreReadModel | None = None
    qualite_comptes: AccountQualityScoreReadModel | None = None
    parcours_scolaire: EducationScoreReadModel | None = None
    continuite_parcours: ContinuityScoreReadModel | None = None
    bonus_malus: BonusMalusReadModel | None = None


class CvQualityReadModel(BaseModel):
    """CV quality evaluation result (/20)."""

    model_config = ConfigDict(frozen=True)

    niveau_experience: str  # JUNIOR, CONFIRME, SENIOR
    annees_experience: float = 0
    note_globale: float  # 0-20
    details_notes: CvQualityDetailsNotesReadModel | None = None
    points_forts: list[str] = []
    points_faibles: list[str] = []
    synthese: str = ""
    classification: str  # EXCELLENT, BON, MOYEN, FAIBLE


class JobPostingReadModel(BaseModel):
    """Job posting read model."""

    model_config = ConfigDict(frozen=True)

    id: str
    opportunity_id: str
    boond_opportunity_id: str | None = None  # Boond external ID for API calls
    opportunity_title: str | None = None
    opportunity_reference: str | None = None
    client_name: str | None = None
    title: str
    description: str
    qualifications: str
    location_country: str
    location_region: str | None = None
    location_postal_code: str | None = None
    location_city: str | None = None
    location_key: str | None = None  # Turnover-IT location key
    contract_types: list[str]
    skills: list[str]
    experience_level: str | None = None
    remote: str | None = None
    start_date: date | None = None
    duration_months: int | None = None
    salary_min_annual: float | None = None
    salary_max_annual: float | None = None
    salary_min_daily: float | None = None
    salary_max_daily: float | None = None
    employer_overview: str | None = None
    status: str
    status_display: str
    turnoverit_reference: str | None = None
    turnoverit_public_url: str | None = None
    application_token: str
    application_url: str | None = None
    created_by: str | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    closed_at: datetime | None = None
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
    location_region: str | None = None
    location_city: str | None = None
    contract_types: list[str]
    skills: list[str]
    experience_level: str | None = None
    remote: str | None = None
    start_date: date | None = None
    duration_months: int | None = None
    salary_min_daily: float | None = None
    salary_max_daily: float | None = None
    employer_overview: str | None = None


class StatusChangeReadModel(BaseModel):
    """Status change history item."""

    model_config = ConfigDict(frozen=True)

    from_status: str
    to_status: str
    changed_at: datetime
    changed_by: str | None = None
    changed_by_name: str | None = None
    comment: str | None = None


class JobApplicationReadModel(BaseModel):
    """Job application read model."""

    model_config = ConfigDict(frozen=True)

    id: str
    job_posting_id: str
    job_posting_title: str | None = None
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
    tjm_current: float | None = None
    tjm_desired: float | None = None
    salary_current: float | None = None
    salary_desired: float | None = None
    tjm_range: str
    salary_range: str
    # Legacy fields (kept for backward compatibility)
    tjm_min: float | None = None
    tjm_max: float | None = None
    availability_date: date | None = None
    cv_s3_key: str
    cv_filename: str
    cv_download_url: str | None = None
    matching_score: int | None = None
    matching_details: MatchingDetailsReadModel | None = None
    # CV Quality evaluation (/20)
    cv_quality_score: float | None = None
    cv_quality: CvQualityReadModel | None = None
    # Read state (separate from status)
    is_read: bool = False
    status: str
    status_display: str
    status_history: list[StatusChangeReadModel] = []
    notes: str | None = None
    boond_candidate_id: str | None = None
    boond_sync_error: str | None = None
    boond_synced_at: datetime | None = None
    boond_sync_status: str = "not_applicable"
    civility: str | None = None
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
