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
from app.dependencies import AppSettings, Boond, DbSession
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


class UpdateJobPostingRequest(BaseModel):
    """Request body for updating a job posting."""

    title: Optional[str] = Field(None, min_length=5, max_length=100)
    description: Optional[str] = Field(None, min_length=500, max_length=3000)
    qualifications: Optional[str] = Field(None, min_length=150, max_length=3000)
    location_country: Optional[str] = Field(None, min_length=2, max_length=50)
    location_region: Optional[str] = Field(None, max_length=100)
    location_postal_code: Optional[str] = Field(None, max_length=20)
    location_city: Optional[str] = Field(None, max_length=100)
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


# --- Opportunities Endpoints ---


@router.get("/opportunities", response_model=OpportunityListForHRReadModel)
async def list_opportunities_for_hr(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    authorization: str = Header(default=""),
):
    """List all open opportunities with job posting status.

    Returns opportunities from BoondManager with information about
    whether a job posting exists and application counts.
    """
    await require_hr_access(db, authorization)

    opportunity_repo = OpportunityRepository(db)
    job_posting_repo = JobPostingRepository(db)
    job_application_repo = JobApplicationRepository(db)

    use_case = ListOpenOpportunitiesForHRUseCase(
        opportunity_repository=opportunity_repo,
        job_posting_repository=job_posting_repo,
        job_application_repository=job_application_repo,
    )

    return await use_case.execute(
        page=page,
        page_size=page_size,
        search=search,
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
