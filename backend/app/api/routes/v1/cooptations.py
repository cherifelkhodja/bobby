"""Cooptation endpoints."""

import logging
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

from app.api.schemas.cooptation import (
    CooptationListResponse,
    CooptationResponse,
    CooptationStatsResponse,
    CvDownloadUrlResponse,
    UpdateCooptationStatusRequest,
)
from app.application.use_cases.cooptations import (
    CreateCooptationCommand,
    CreateCooptationUseCase,
    GetCooptationStatsUseCase,
    GetCooptationUseCase,
    ListCooptationsUseCase,
    UpdateCooptationStatusUseCase,
)
from app.dependencies import AppSettings, Boond, DbSession
from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    CooptationNotFoundError,
    OpportunityNotFoundError,
)
from app.domain.value_objects import CooptationStatus
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    OpportunityRepository,
    PublishedOpportunityRepository,
    UserRepository,
)
from app.infrastructure.email.sender import EmailService
from app.infrastructure.security.jwt import decode_token
from app.infrastructure.storage.s3_client import S3StorageClient

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_CV_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CV_EXTENSIONS = {".pdf", ".docx", ".doc"}
ALLOWED_CV_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def get_user_id_from_auth(authorization: str) -> UUID:
    """Extract user ID from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    return UUID(payload.sub)


async def _validate_cv(cv: UploadFile) -> tuple[bytes, str, str]:
    """Validate CV file and return (content, filename, content_type)."""
    if not cv.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    ext = os.path.splitext(cv.filename)[1].lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Format de fichier non supporté. Utilisez PDF ou DOCX.",
        )

    if cv.content_type and cv.content_type not in ALLOWED_CV_TYPES:
        # Allow unknown content types if extension is valid
        if cv.content_type != "application/octet-stream":
            raise HTTPException(
                status_code=400,
                detail="Type de fichier non supporté. Utilisez PDF ou DOCX.",
            )

    content = await cv.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide")
    if len(content) > MAX_CV_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Le fichier est trop volumineux. Maximum 10 Mo.",
        )

    return content, cv.filename, cv.content_type or "application/octet-stream"


@router.post("", response_model=CooptationResponse, status_code=201)
async def create_cooptation(
    db: DbSession,
    boond: Boond,
    settings: AppSettings,
    opportunity_id: str = Form(...),
    candidate_first_name: str = Form(..., min_length=1, max_length=100),
    candidate_last_name: str = Form(..., min_length=1, max_length=100),
    candidate_email: str = Form(...),
    candidate_civility: str = Form(default="M"),
    candidate_phone: str | None = Form(default=None),
    candidate_daily_rate: float | None = Form(default=None),
    candidate_note: str | None = Form(default=None),
    cv: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    """Create a new cooptation with CV upload."""
    user_id = get_user_id_from_auth(authorization)

    # Validate CV
    cv_content, cv_original_filename, cv_content_type = await _validate_cv(cv)

    # Upload CV to S3
    s3_client = S3StorageClient(settings)
    file_ext = os.path.splitext(cv_original_filename)[1].lower()
    upload_date = datetime.utcnow().strftime("%Y%m%d")
    formatted_name = f"{candidate_first_name} {candidate_last_name.upper()}"
    cv_display_name = f"{formatted_name} - {upload_date}{file_ext}"
    cv_s3_key = f"cooptations/{opportunity_id}/{cv_display_name}"

    try:
        await s3_client.upload_file(
            key=cv_s3_key,
            content=cv_content,
            content_type=cv_content_type,
        )
    except Exception:
        logger.exception("Failed to upload CV to S3")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors du téléchargement du CV",
        )

    # Create cooptation
    cooptation_repo = CooptationRepository(db)
    candidate_repo = CandidateRepository(db)
    opportunity_repo = OpportunityRepository(db)
    published_opportunity_repo = PublishedOpportunityRepository(db)
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = CreateCooptationUseCase(
        cooptation_repo,
        candidate_repo,
        opportunity_repo,
        published_opportunity_repo,
        user_repo,
        boond,
        email_service,
    )

    command = CreateCooptationCommand(
        opportunity_id=UUID(opportunity_id),
        submitter_id=user_id,
        candidate_first_name=candidate_first_name,
        candidate_last_name=candidate_last_name,
        candidate_email=candidate_email,
        candidate_civility=candidate_civility,
        candidate_phone=candidate_phone,
        candidate_daily_rate=candidate_daily_rate,
        candidate_note=candidate_note,
        cv_s3_key=cv_s3_key,
        cv_filename=cv_display_name,
    )

    try:
        result = await use_case.execute(command)
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")
    except CandidateAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("Error creating cooptation for opportunity %s", opportunity_id)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la cooptation",
        )

    return CooptationResponse(**result.model_dump())


@router.get("", response_model=CooptationListResponse)
async def list_cooptations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    opportunity_id: str | None = Query(None),
    authorization: str = Header(default=""),
):
    """List all cooptations with optional filters."""
    get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)

    status_filter = CooptationStatus(status) if status else None
    opp_id = UUID(opportunity_id) if opportunity_id else None

    # Resolve published opportunity ID to actual opportunity ID.
    # Cooptations reference the synced opportunity (from Boond), which may
    # have a different UUID than the published_opportunity.id.
    if opp_id:
        published_repo = PublishedOpportunityRepository(db)
        published = await published_repo.get_by_id(opp_id)
        if published:
            opportunity_repo = OpportunityRepository(db)
            opp = await opportunity_repo.get_by_external_id(
                published.boond_opportunity_id
            )
            if opp:
                opp_id = opp.id

    use_case = ListCooptationsUseCase(cooptation_repo, user_repo)
    result = await use_case.execute(
        page=page,
        page_size=page_size,
        status=status_filter,
        opportunity_id=opp_id,
    )

    return CooptationListResponse(
        items=[CooptationResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/me", response_model=CooptationListResponse)
async def list_my_cooptations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    authorization: str = Header(default=""),
):
    """List current user's cooptations."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)

    use_case = ListCooptationsUseCase(cooptation_repo, user_repo)
    result = await use_case.execute(
        page=page,
        page_size=page_size,
        submitter_id=user_id,
    )

    return CooptationListResponse(
        items=[CooptationResponse(**item.model_dump()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/me/stats", response_model=CooptationStatsResponse)
async def get_my_stats(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get current user's cooptation statistics."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationStatsUseCase(cooptation_repo)
    result = await use_case.execute(submitter_id=user_id)

    return CooptationStatsResponse(**result.model_dump())


@router.get("/stats", response_model=CooptationStatsResponse)
async def get_all_stats(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get overall cooptation statistics (admin view)."""
    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationStatsUseCase(cooptation_repo)
    result = await use_case.execute()

    return CooptationStatsResponse(**result.model_dump())


@router.get("/{cooptation_id}", response_model=CooptationResponse)
async def get_cooptation(
    cooptation_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get cooptation details."""
    cooptation_repo = CooptationRepository(db)

    use_case = GetCooptationUseCase(cooptation_repo)
    result = await use_case.execute(cooptation_id)

    return CooptationResponse(**result.model_dump())


@router.get("/{cooptation_id}/cv", response_model=CvDownloadUrlResponse)
async def get_cooptation_cv_url(
    cooptation_id: UUID,
    db: DbSession,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Get presigned URL for candidate CV download.

    Access: admin or commercial owner of the linked opportunity.
    """
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)

    # Get cooptation
    cooptation = await cooptation_repo.get_by_id(cooptation_id)
    if not cooptation:
        raise CooptationNotFoundError(str(cooptation_id))

    # Check authorization: admin or commercial owner
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    is_admin = str(user.role) == "admin"
    is_owner = cooptation.opportunity.owner_id == user_id
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux administrateurs et au commercial responsable",
        )

    # Check candidate has a CV
    if not cooptation.candidate.cv_path:
        raise HTTPException(status_code=404, detail="Aucun CV associé à ce candidat")

    # Generate presigned URL
    s3_client = S3StorageClient(settings)
    expires_in = 3600
    try:
        url = await s3_client.get_presigned_url(
            key=cooptation.candidate.cv_path,
            expires_in=expires_in,
        )
    except Exception:
        logger.exception("Failed to generate presigned URL for CV")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la génération du lien de téléchargement",
        )

    return CvDownloadUrlResponse(
        url=url,
        filename=cooptation.candidate.cv_filename or "cv",
        expires_in=expires_in,
    )


@router.patch("/{cooptation_id}/status", response_model=CooptationResponse)
async def update_cooptation_status(
    cooptation_id: UUID,
    request: UpdateCooptationStatusRequest,
    db: DbSession,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Update cooptation status (admin only)."""
    user_id = get_user_id_from_auth(authorization)

    cooptation_repo = CooptationRepository(db)
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = UpdateCooptationStatusUseCase(
        cooptation_repo,
        user_repo,
        email_service,
    )

    new_status = CooptationStatus(request.status)
    result = await use_case.execute(
        cooptation_id=cooptation_id,
        new_status=new_status,
        changed_by=user_id,
        comment=request.comment,
    )

    return CooptationResponse(**result.model_dump())
