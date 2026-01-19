"""HR API endpoints for job postings and applications management."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.application.read_models.hr import (
    JobApplicationListReadModel,
    JobApplicationReadModel,
    JobPostingListReadModel,
    JobPostingReadModel,
    OpportunityListForHRReadModel,
)
from app.application.use_cases.job_applications import (
    CreateCandidateInBoondUseCase,
    GetApplicationCvUrlUseCase,
    GetApplicationUseCase,
    ListApplicationsForPostingUseCase,
    UpdateApplicationNoteUseCase,
    UpdateApplicationStatusCommand,
    UpdateApplicationStatusUseCase,
)
from app.application.use_cases.job_postings import (
    CloseJobPostingUseCase,
    CreateJobPostingCommand,
    CreateJobPostingUseCase,
    GetJobPostingUseCase,
    ListJobPostingsUseCase,
    ListOpenOpportunitiesForHRUseCase,
    PublishJobPostingUseCase,
    UpdateJobPostingCommand,
    UpdateJobPostingUseCase,
)
from app.config import settings
from app.dependencies import AppSettings, AppSettingsSvc, Boond, DbSession
from app.domain.entities import ApplicationStatus, JobPostingStatus
from app.domain.exceptions import (
    InvalidStatusTransitionError,
    JobApplicationNotFoundError,
    JobPostingNotFoundError,
    OpportunityNotFoundError,
)
from app.domain.value_objects import UserRole
from app.infrastructure.database.repositories import (
    JobApplicationRepository,
    JobPostingRepository,
    OpportunityRepository,
    UserRepository,
)
from app.infrastructure.anonymizer.job_posting_anonymizer import JobPostingAnonymizer
from app.infrastructure.matching.gemini_matcher import GeminiMatchingService
from app.infrastructure.security.jwt import decode_token
from app.infrastructure.storage.s3_client import S3StorageClient
from app.infrastructure.turnoverit.client import TurnoverITClient

router = APIRouter()

# Allowed roles for HR features
HR_ROLES = {UserRole.ADMIN, UserRole.RH}


# --- Request/Response Models ---


class CreateJobPostingRequest(BaseModel):
    """Request body for creating a job posting."""

    opportunity_id: str
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=500, max_length=3000)
    qualifications: str = Field(..., min_length=150, max_length=3000)
    location_country: str = Field(..., min_length=2, max_length=50)
    location_region: Optional[str] = Field(None, max_length=100)
    location_postal_code: Optional[str] = Field(None, max_length=20)
    location_city: Optional[str] = Field(None, max_length=100)
    location_key: Optional[str] = Field(None, max_length=200)  # Turnover-IT location key
    contract_types: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = Field(None, ge=1, le=120)
    salary_min_annual: Optional[float] = Field(None, ge=0)
    salary_max_annual: Optional[float] = Field(None, ge=0)
    salary_min_daily: Optional[float] = Field(None, ge=0)
    salary_max_daily: Optional[float] = Field(None, ge=0)
    employer_overview: Optional[str] = Field(None, max_length=3000)
    pushToTop: Optional[bool] = Field(default=True)


class UpdateJobPostingRequest(BaseModel):
    """Request body for updating a job posting."""

    title: Optional[str] = Field(None, min_length=5, max_length=100)
    description: Optional[str] = Field(None, min_length=500, max_length=3000)
    qualifications: Optional[str] = Field(None, min_length=150, max_length=3000)
    location_country: Optional[str] = Field(None, min_length=2, max_length=50)
    location_region: Optional[str] = Field(None, max_length=100)
    location_postal_code: Optional[str] = Field(None, max_length=20)
    location_city: Optional[str] = Field(None, max_length=100)
    location_key: Optional[str] = Field(None, max_length=200)  # Turnover-IT location key
    contract_types: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    start_date: Optional[date] = None
    duration_months: Optional[int] = Field(None, ge=1, le=120)
    salary_min_annual: Optional[float] = Field(None, ge=0)
    salary_max_annual: Optional[float] = Field(None, ge=0)
    salary_min_daily: Optional[float] = Field(None, ge=0)
    salary_max_daily: Optional[float] = Field(None, ge=0)
    employer_overview: Optional[str] = Field(None, max_length=3000)


class UpdateApplicationStatusRequest(BaseModel):
    """Request body for updating application status."""

    status: str
    comment: Optional[str] = Field(None, max_length=1000)


class UpdateApplicationNoteRequest(BaseModel):
    """Request body for updating application notes."""

    notes: str = Field(..., max_length=5000)


class CvDownloadUrlResponse(BaseModel):
    """Response with CV download URL."""

    url: str
    filename: str
    expires_in: int


class AnonymizeJobPostingRequest(BaseModel):
    """Request body for anonymizing a job posting."""

    opportunity_id: str
    title: str
    description: str
    client_name: Optional[str] = None


class AnonymizedJobPostingResponse(BaseModel):
    """Response with anonymized job posting content."""

    title: str
    description: str
    qualifications: str
    skills: list[str]  # Turnover-IT skill slugs


class SyncSkillsResponse(BaseModel):
    """Response for skills sync operation."""

    synced_count: int
    message: str


class TurnoverITSkillItem(BaseModel):
    """A single Turnover-IT skill."""

    name: str
    slug: str


class TurnoverITSkillsListResponse(BaseModel):
    """Response with list of Turnover-IT skills."""

    skills: list[TurnoverITSkillItem]
    total: int


class TurnoverITPlaceItem(BaseModel):
    """A single Turnover-IT place from locations autocomplete API."""

    key: str  # Unique identifier for persistence (e.g., "fr~ile-de-france~paris~")
    label: str  # Full display label (e.g., "Paris, France")
    shortLabel: str  # Short label (e.g., "Paris")
    locality: str  # City name (from adminLevel2)
    region: str  # Region name (from adminLevel1)
    postalCode: str  # Postal code
    country: str  # Country name
    countryCode: str  # ISO country code (e.g., "FR")


class TurnoverITPlacesListResponse(BaseModel):
    """Response with list of Turnover-IT places."""

    places: list[TurnoverITPlaceItem]
    total: int


class OpportunityDetailResponse(BaseModel):
    """Response with full opportunity details from BoondManager."""

    id: str
    title: str
    reference: str
    description: Optional[str] = None
    criteria: Optional[str] = None
    expertise_area: Optional[str] = None
    place: Optional[str] = None
    duration: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    agency_id: Optional[str] = None
    agency_name: Optional[str] = None
    state: Optional[int] = None
    state_name: Optional[str] = None
    state_color: Optional[str] = None


# --- Auth Helpers ---


async def get_current_user(
    db: DbSession,
    authorization: str,
) -> tuple[UUID, UserRole]:
    """Verify user authentication and return user ID and role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    return user_id, user.role


async def get_current_user_full(
    db: DbSession,
    authorization: str,
) -> tuple[UUID, UserRole, Optional[str]]:
    """Verify user authentication and return user ID, role, and boond_resource_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    return user_id, user.role, user.boond_resource_id


async def require_hr_access(
    db: DbSession,
    authorization: str,
) -> UUID:
    """Verify user has HR access (admin or rh role)."""
    user_id, role = await get_current_user(db, authorization)

    if role not in HR_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux RH et administrateurs",
        )

    return user_id


# --- Anonymization Endpoints ---


@router.post("/anonymize-job-posting", response_model=AnonymizedJobPostingResponse)
async def anonymize_job_posting(
    db: DbSession,
    app_settings: AppSettings,
    app_settings_svc: AppSettingsSvc,
    request: AnonymizeJobPostingRequest,
    authorization: str = Header(default=""),
):
    """Anonymize opportunity content for a job posting.

    Uses Gemini AI to:
    - Anonymize client names and internal references
    - Structure content for Turnover-IT (title, description, qualifications)
    - Extract and match skills to Turnover-IT nomenclature

    Returns anonymized content that can be edited before creating the posting.
    """
    await require_hr_access(db, authorization)

    # Get configured Gemini model from database settings
    model_name = await app_settings_svc.get_gemini_model()

    turnoverit_client = TurnoverITClient(app_settings)
    anonymizer = JobPostingAnonymizer(
        settings=app_settings,
        db_session=db,
        turnoverit_client=turnoverit_client,
    )

    try:
        result = await anonymizer.anonymize(
            title=request.title,
            description=request.description,
            client_name=request.client_name,
            model_name=model_name,
        )
        return AnonymizedJobPostingResponse(
            title=result.title,
            description=result.description,
            qualifications=result.qualifications,
            skills=result.skills,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'anonymisation: {str(e)}",
        )


@router.post("/sync-skills", response_model=SyncSkillsResponse)
async def sync_turnoverit_skills(
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Manually sync Turnover-IT skills to the database.

    This fetches all skills from the Turnover-IT API and stores them
    in the local database for faster matching during anonymization.
    """
    # Only admin can force sync
    user_id, role = await get_current_user(db, authorization)
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent synchroniser les skills",
        )

    turnoverit_client = TurnoverITClient(app_settings)
    anonymizer = JobPostingAnonymizer(
        settings=app_settings,
        db_session=db,
        turnoverit_client=turnoverit_client,
    )

    try:
        count = await anonymizer.sync_skills()
        return SyncSkillsResponse(
            synced_count=count,
            message=f"{count} compétences synchronisées depuis Turnover-IT",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la synchronisation: {str(e)}",
        )


@router.get("/skills", response_model=TurnoverITSkillsListResponse)
async def get_turnoverit_skills(
    db: DbSession,
    search: Optional[str] = Query(None, max_length=100),
    authorization: str = Header(default=""),
):
    """Get Turnover-IT skills from the database cache.

    Returns the list of skills from the local database cache.
    Skills are synced periodically from Turnover-IT API.

    - search: Optional search term to filter skills by name
    """
    await require_hr_access(db, authorization)

    from sqlalchemy import text

    # Check if table exists (might not in some environments)
    check_query = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'turnoverit_skills'
        )
    """)
    result = await db.execute(check_query)
    table_exists = result.scalar()

    if not table_exists:
        return TurnoverITSkillsListResponse(skills=[], total=0)

    # Build query with optional search filter
    if search:
        query = text("""
            SELECT name, slug FROM turnoverit_skills
            WHERE LOWER(name) LIKE LOWER(:search)
            ORDER BY name ASC
        """)
        result = await db.execute(query, {"search": f"%{search}%"})
    else:
        query = text("""
            SELECT name, slug FROM turnoverit_skills
            ORDER BY name ASC
        """)
        result = await db.execute(query)

    rows = result.fetchall()
    skills = [TurnoverITSkillItem(name=row[0], slug=row[1]) for row in rows]

    return TurnoverITSkillsListResponse(skills=skills, total=len(skills))


@router.get("/places", response_model=TurnoverITPlacesListResponse)
async def get_turnoverit_places(
    db: DbSession,
    settings: AppSettings,
    q: str = Query(..., min_length=2, max_length=100),
    authorization: str = Header(default=""),
):
    """Get place suggestions from Turnover-IT.

    Search for cities, regions, or postal codes to use for job locations.

    - q: Search query (min 2 characters)
    """
    await require_hr_access(db, authorization)

    turnoverit_client = TurnoverITClient(settings)
    places = await turnoverit_client.get_places(q)

    return TurnoverITPlacesListResponse(
        places=[TurnoverITPlaceItem(**place) for place in places],
        total=len(places),
    )


# --- Opportunities Endpoints ---


@router.get("/opportunities", response_model=OpportunityListForHRReadModel)
async def list_opportunities_for_hr(
    db: DbSession,
    boond_client: Boond,
    search: Optional[str] = Query(None, max_length=100),
    authorization: str = Header(default=""),
):
    """List opportunities from BoondManager where user is HR manager.

    Returns opportunities from BoondManager API filtered by hrManager,
    enriched with job posting status and application counts.

    - For admin users: Returns ALL opportunities (admin view)
    - For RH users: Returns only opportunities where they are HR manager
    """
    user_id, role, boond_resource_id = await get_current_user_full(db, authorization)

    if role not in HR_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux RH et administrateurs",
        )

    is_admin = role == UserRole.ADMIN

    job_posting_repo = JobPostingRepository(db)
    job_application_repo = JobApplicationRepository(db)

    use_case = ListOpenOpportunitiesForHRUseCase(
        boond_client=boond_client,
        job_posting_repository=job_posting_repo,
        job_application_repository=job_application_repo,
    )

    try:
        return await use_case.execute(
            hr_manager_boond_id=boond_resource_id,
            is_admin=is_admin,
            search=search,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailResponse)
async def get_opportunity_detail(
    opportunity_id: str,
    db: DbSession,
    boond_client: Boond,
    authorization: str = Header(default=""),
):
    """Get detailed opportunity information from BoondManager.

    Returns full opportunity details including description, criteria,
    company name, manager name, etc.
    """
    await require_hr_access(db, authorization)

    try:
        detail = await boond_client.get_opportunity_information(opportunity_id)
        return OpportunityDetailResponse(**detail)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'opportunité: {str(e)}",
        )


# --- Job Postings Endpoints ---


@router.post("/job-postings", response_model=JobPostingReadModel)
async def create_job_posting(
    db: DbSession,
    request: CreateJobPostingRequest,
    authorization: str = Header(default=""),
):
    """Create a new job posting draft."""
    user_id = await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    user_repo = UserRepository(db)

    use_case = CreateJobPostingUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        user_repository=user_repo,
    )

    try:
        command = CreateJobPostingCommand(
            opportunity_id=UUID(request.opportunity_id),
            created_by=user_id,
            title=request.title,
            description=request.description,
            qualifications=request.qualifications,
            location_country=request.location_country,
            location_region=request.location_region,
            location_postal_code=request.location_postal_code,
            location_city=request.location_city,
            location_key=request.location_key,
            contract_types=request.contract_types,
            skills=request.skills,
            experience_level=request.experience_level,
            remote=request.remote,
            start_date=request.start_date,
            duration_months=request.duration_months,
            salary_min_annual=request.salary_min_annual,
            salary_max_annual=request.salary_max_annual,
            salary_min_daily=request.salary_min_daily,
            salary_max_daily=request.salary_max_daily,
            employer_overview=request.employer_overview,
        )
        return await use_case.execute(command)
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-postings", response_model=JobPostingListReadModel)
async def list_job_postings(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    authorization: str = Header(default=""),
):
    """List all job postings."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    job_application_repo = JobApplicationRepository(db)
    user_repo = UserRepository(db)

    use_case = ListJobPostingsUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        job_application_repository=job_application_repo,
        user_repository=user_repo,
    )

    status_enum = JobPostingStatus(status) if status else None

    return await use_case.execute(
        page=page,
        page_size=page_size,
        status=status_enum,
    )


@router.get("/job-postings/{posting_id}", response_model=JobPostingReadModel)
async def get_job_posting(
    posting_id: str,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get job posting details."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    job_application_repo = JobApplicationRepository(db)
    user_repo = UserRepository(db)

    use_case = GetJobPostingUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        job_application_repository=job_application_repo,
        user_repository=user_repo,
    )

    try:
        return await use_case.execute(UUID(posting_id))
    except JobPostingNotFoundError:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")


@router.patch("/job-postings/{posting_id}", response_model=JobPostingReadModel)
async def update_job_posting(
    posting_id: str,
    db: DbSession,
    request: UpdateJobPostingRequest,
    authorization: str = Header(default=""),
):
    """Update a draft job posting."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    user_repo = UserRepository(db)

    use_case = UpdateJobPostingUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        user_repository=user_repo,
    )

    try:
        command = UpdateJobPostingCommand(
            posting_id=UUID(posting_id),
            title=request.title,
            description=request.description,
            qualifications=request.qualifications,
            location_country=request.location_country,
            location_region=request.location_region,
            location_postal_code=request.location_postal_code,
            location_city=request.location_city,
            location_key=request.location_key,
            contract_types=request.contract_types,
            skills=request.skills,
            experience_level=request.experience_level,
            remote=request.remote,
            start_date=request.start_date,
            duration_months=request.duration_months,
            salary_min_annual=request.salary_min_annual,
            salary_max_annual=request.salary_max_annual,
            salary_min_daily=request.salary_min_daily,
            salary_max_daily=request.salary_max_daily,
            employer_overview=request.employer_overview,
        )
        return await use_case.execute(command)
    except JobPostingNotFoundError:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/job-postings/{posting_id}/publish", response_model=JobPostingReadModel)
async def publish_job_posting(
    posting_id: str,
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Publish a job posting to Turnover-IT."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    user_repo = UserRepository(db)
    turnoverit_client = TurnoverITClient(app_settings)

    use_case = PublishJobPostingUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        user_repository=user_repo,
        turnoverit_client=turnoverit_client,
    )

    try:
        return await use_case.execute(UUID(posting_id))
    except JobPostingNotFoundError:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la publication: {str(e)}",
        )


@router.post("/job-postings/{posting_id}/close", response_model=JobPostingReadModel)
async def close_job_posting(
    posting_id: str,
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Close a published job posting."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    opportunity_repo = OpportunityRepository(db)
    user_repo = UserRepository(db)
    turnoverit_client = TurnoverITClient(app_settings)

    use_case = CloseJobPostingUseCase(
        job_posting_repository=job_posting_repo,
        opportunity_repository=opportunity_repo,
        user_repository=user_repo,
        turnoverit_client=turnoverit_client,
    )

    try:
        return await use_case.execute(UUID(posting_id))
    except JobPostingNotFoundError:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Applications Endpoints ---


@router.get(
    "/job-postings/{posting_id}/applications",
    response_model=JobApplicationListReadModel,
)
async def list_applications_for_posting(
    posting_id: str,
    db: DbSession,
    app_settings: AppSettings,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    sort_by_score: bool = Query(True),
    authorization: str = Header(default=""),
):
    """List applications for a job posting."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    job_application_repo = JobApplicationRepository(db)
    s3_client = S3StorageClient(app_settings)

    use_case = ListApplicationsForPostingUseCase(
        job_posting_repository=job_posting_repo,
        job_application_repository=job_application_repo,
        s3_client=s3_client,
    )

    status_enum = ApplicationStatus(status) if status else None

    try:
        return await use_case.execute(
            posting_id=UUID(posting_id),
            page=page,
            page_size=page_size,
            status=status_enum,
            sort_by_score=sort_by_score,
        )
    except JobPostingNotFoundError:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")


@router.get("/applications/{application_id}", response_model=JobApplicationReadModel)
async def get_application(
    application_id: str,
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Get application details."""
    await require_hr_access(db, authorization)

    job_posting_repo = JobPostingRepository(db)
    job_application_repo = JobApplicationRepository(db)
    s3_client = S3StorageClient(app_settings)

    use_case = GetApplicationUseCase(
        job_posting_repository=job_posting_repo,
        job_application_repository=job_application_repo,
        s3_client=s3_client,
    )

    try:
        return await use_case.execute(UUID(application_id))
    except JobApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")


@router.patch(
    "/applications/{application_id}/status",
    response_model=JobApplicationReadModel,
)
async def update_application_status(
    application_id: str,
    db: DbSession,
    app_settings: AppSettings,
    request: UpdateApplicationStatusRequest,
    authorization: str = Header(default=""),
):
    """Update application status."""
    user_id = await require_hr_access(db, authorization)

    job_application_repo = JobApplicationRepository(db)
    job_posting_repo = JobPostingRepository(db)
    user_repo = UserRepository(db)
    s3_client = S3StorageClient(app_settings)

    use_case = UpdateApplicationStatusUseCase(
        job_application_repository=job_application_repo,
        job_posting_repository=job_posting_repo,
        user_repository=user_repo,
        s3_client=s3_client,
    )

    try:
        status_enum = ApplicationStatus(request.status)
        command = UpdateApplicationStatusCommand(
            application_id=UUID(application_id),
            new_status=status_enum,
            changed_by=user_id,
            comment=request.comment,
        )
        return await use_case.execute(command)
    except JobApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/applications/{application_id}/note",
    response_model=JobApplicationReadModel,
)
async def update_application_note(
    application_id: str,
    db: DbSession,
    app_settings: AppSettings,
    request: UpdateApplicationNoteRequest,
    authorization: str = Header(default=""),
):
    """Update application notes."""
    await require_hr_access(db, authorization)

    job_application_repo = JobApplicationRepository(db)
    job_posting_repo = JobPostingRepository(db)
    s3_client = S3StorageClient(app_settings)

    use_case = UpdateApplicationNoteUseCase(
        job_application_repository=job_application_repo,
        job_posting_repository=job_posting_repo,
        s3_client=s3_client,
    )

    try:
        return await use_case.execute(
            application_id=UUID(application_id),
            notes=request.notes,
        )
    except JobApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")


@router.get(
    "/applications/{application_id}/cv",
    response_model=CvDownloadUrlResponse,
)
async def get_application_cv_url(
    application_id: str,
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Get presigned URL to download application CV."""
    await require_hr_access(db, authorization)

    job_application_repo = JobApplicationRepository(db)
    s3_client = S3StorageClient(app_settings)

    # Get application first to get filename
    application = await job_application_repo.get_by_id(UUID(application_id))
    if not application:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")

    use_case = GetApplicationCvUrlUseCase(
        job_application_repository=job_application_repo,
        s3_client=s3_client,
    )

    try:
        expires_in = 3600  # 1 hour
        url = await use_case.execute(
            application_id=UUID(application_id),
            expires_in=expires_in,
        )
        return CvDownloadUrlResponse(
            url=url,
            filename=application.cv_filename,
            expires_in=expires_in,
        )
    except JobApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du lien: {str(e)}",
        )


@router.post(
    "/applications/{application_id}/create-in-boond",
    response_model=JobApplicationReadModel,
)
async def create_candidate_in_boond(
    application_id: str,
    db: DbSession,
    app_settings: AppSettings,
    boond_client: Boond,
    authorization: str = Header(default=""),
):
    """Create candidate in BoondManager from application."""
    await require_hr_access(db, authorization)

    job_application_repo = JobApplicationRepository(db)
    job_posting_repo = JobPostingRepository(db)
    s3_client = S3StorageClient(app_settings)

    use_case = CreateCandidateInBoondUseCase(
        job_application_repository=job_application_repo,
        job_posting_repository=job_posting_repo,
        boond_client=boond_client,
        s3_client=s3_client,
    )

    try:
        return await use_case.execute(UUID(application_id))
    except JobApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
