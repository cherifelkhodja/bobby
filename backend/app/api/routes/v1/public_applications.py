"""Public API endpoints for job applications (no authentication required)."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field

from app.application.read_models.hr import (
    ApplicationSubmissionResultReadModel,
    JobPostingPublicReadModel,
)
from app.application.use_cases.job_applications import (
    SubmitApplicationCommand,
    SubmitApplicationUseCase,
)
from app.application.use_cases.job_postings import GetJobPostingByTokenUseCase
from app.dependencies import AppSettings, DbSession
from app.domain.exceptions import JobPostingNotFoundError
from app.infrastructure.database.repositories import (
    JobApplicationRepository,
    JobPostingRepository,
)
from app.infrastructure.matching.gemini_matcher import GeminiMatchingService
from app.infrastructure.storage.s3_client import S3StorageClient

router = APIRouter()

# Maximum CV file size (10 MB)
MAX_CV_SIZE = 10 * 1024 * 1024

# Allowed CV file types
ALLOWED_CV_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_CV_EXTENSIONS = {".pdf", ".docx"}


class ApplicationFormRequest(BaseModel):
    """Request body for application submission (for documentation)."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=30, pattern=r"^\+?[0-9\s\-]+$")
    job_title: str = Field(..., min_length=1, max_length=200)
    tjm_min: float = Field(..., ge=0)
    tjm_max: float = Field(..., ge=0)
    availability_date: date


@router.get("/{token}", response_model=JobPostingPublicReadModel)
async def get_public_job_posting(
    token: str,
    db: DbSession,
):
    """Get public job posting information by application token.

    This endpoint is public and does not require authentication.
    Returns only the information needed for the application form.
    """
    job_posting_repo = JobPostingRepository(db)

    use_case = GetJobPostingByTokenUseCase(
        job_posting_repository=job_posting_repo,
    )

    try:
        return await use_case.execute(token)
    except JobPostingNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Cette offre d'emploi n'existe pas ou n'est plus disponible.",
        )


@router.post("/{token}", response_model=ApplicationSubmissionResultReadModel)
async def submit_application(
    token: str,
    db: DbSession,
    app_settings: AppSettings,
    first_name: str = Form(..., min_length=1, max_length=100),
    last_name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    phone: str = Form(..., min_length=10, max_length=30),
    job_title: str = Form(..., min_length=1, max_length=200),
    tjm_min: float = Form(..., ge=0),
    tjm_max: float = Form(..., ge=0),
    availability_date: date = Form(...),
    cv: UploadFile = File(...),
):
    """Submit a job application through the public form.

    This endpoint is public and does not require authentication.
    Accepts multipart/form-data with CV file upload.

    The CV is uploaded to S3 and analyzed using AI to calculate
    a matching score against the job requirements.
    """
    # Validate email format
    try:
        from pydantic import validate_email
        validate_email(email)
    except Exception:
        raise HTTPException(status_code=400, detail="Adresse email invalide")

    # Validate phone format (basic check for French phone)
    phone = phone.strip()
    if not phone.replace("+", "").replace(" ", "").replace("-", "").isdigit():
        raise HTTPException(
            status_code=400,
            detail="Numéro de téléphone invalide. Utilisez le format +33...",
        )

    # Validate TJM range
    if tjm_max < tjm_min:
        raise HTTPException(
            status_code=400,
            detail="Le TJM maximum doit être supérieur ou égal au TJM minimum",
        )

    # Validate CV file
    if not cv.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier CV manquant")

    # Check file extension
    file_lower = cv.filename.lower()
    if not any(file_lower.endswith(ext) for ext in ALLOWED_CV_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Format de CV non supporté. Utilisez PDF ou DOCX.",
        )

    # Check content type
    if cv.content_type and cv.content_type not in ALLOWED_CV_TYPES:
        # Allow unknown content type if extension is valid
        pass

    # Read CV content
    cv_content = await cv.read()

    # Check file size
    if len(cv_content) > MAX_CV_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Le fichier CV est trop volumineux. Maximum {MAX_CV_SIZE // (1024*1024)} Mo.",
        )

    if len(cv_content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier CV est vide")

    # Determine content type from extension if not provided
    content_type = cv.content_type
    if not content_type:
        if file_lower.endswith(".pdf"):
            content_type = "application/pdf"
        else:
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Create services
    job_posting_repo = JobPostingRepository(db)
    job_application_repo = JobApplicationRepository(db)
    s3_client = S3StorageClient(app_settings)
    matching_service = GeminiMatchingService(app_settings)

    use_case = SubmitApplicationUseCase(
        job_posting_repository=job_posting_repo,
        job_application_repository=job_application_repo,
        s3_client=s3_client,
        matching_service=matching_service,
    )

    try:
        command = SubmitApplicationCommand(
            application_token=token,
            first_name=first_name.strip(),
            last_name=last_name.strip().upper(),
            email=email.strip().lower(),
            phone=phone,
            job_title=job_title.strip(),
            tjm_min=tjm_min,
            tjm_max=tjm_max,
            availability_date=availability_date,
            cv_content=cv_content,
            cv_filename=cv.filename,
            cv_content_type=content_type,
        )
        return await use_case.execute(command)
    except JobPostingNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Cette offre d'emploi n'existe pas ou n'est plus disponible.",
        )
    except Exception as e:
        # Log the error but return generic message
        print(f"[Application Submit] Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Une erreur s'est produite lors de la soumission. Veuillez réessayer.",
        )
