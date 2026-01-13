"""CV Transformer API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.application.use_cases.cv_transformer import (
    GetTemplatesUseCase,
    GetTransformationStatsUseCase,
    TransformCvUseCase,
    UploadTemplateUseCase,
)
from app.config import settings
from app.dependencies import AppSettings, DbSession
from app.domain.value_objects import UserRole
from app.infrastructure.cv_transformer import (
    DocxGenerator,
    DocxTextExtractor,
    GeminiClient,
    PdfTextExtractor,
)
from app.infrastructure.database.repositories import (
    CvTemplateRepository,
    CvTransformationLogRepository,
    UserRepository,
)
from app.infrastructure.security.jwt import decode_token

router = APIRouter()

# Allowed roles for CV transformation
ALLOWED_ROLES = {UserRole.ADMIN, UserRole.COMMERCIAL, UserRole.RH}

# Maximum file size (16 MB)
MAX_FILE_SIZE = 16 * 1024 * 1024


class TemplateResponse(BaseModel):
    """Template info response."""

    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    is_active: bool
    updated_at: str


class TemplatesListResponse(BaseModel):
    """List of templates response."""

    templates: list[TemplateResponse]


class TransformationStatsResponse(BaseModel):
    """Transformation statistics response."""

    total: int
    by_user: list[dict]


async def get_current_user(
    db: DbSession,
    authorization: str,
) -> tuple[UUID, UserRole]:
    """Verify user authentication and return user ID and role.

    Args:
        db: Database session.
        authorization: Authorization header.

    Returns:
        Tuple of (user_id, user_role).

    Raises:
        HTTPException: If authentication fails.
    """
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


async def require_transformer_access(
    db: DbSession,
    authorization: str,
) -> UUID:
    """Verify user has access to CV transformer (admin, commercial, or rh).

    Args:
        db: Database session.
        authorization: Authorization header.

    Returns:
        User ID.

    Raises:
        HTTPException: If access is denied.
    """
    user_id, role = await get_current_user(db, authorization)

    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux administrateurs, commerciaux et RH",
        )

    return user_id


async def require_admin(db: DbSession, authorization: str) -> UUID:
    """Verify user is admin.

    Args:
        db: Database session.
        authorization: Authorization header.

    Returns:
        User ID.

    Raises:
        HTTPException: If not admin.
    """
    user_id, role = await get_current_user(db, authorization)

    if role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accès administrateur requis")

    return user_id


@router.get("/templates", response_model=TemplatesListResponse)
async def list_templates(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """List available CV templates.

    Returns only active templates for non-admin users.
    """
    user_id, role = await get_current_user(db, authorization)

    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux administrateurs, commerciaux et RH",
        )

    template_repo = CvTemplateRepository(db)
    use_case = GetTemplatesUseCase(template_repo)

    # Admins can see inactive templates too
    include_inactive = role == UserRole.ADMIN
    templates = await use_case.execute(include_inactive=include_inactive)

    return TemplatesListResponse(
        templates=[TemplateResponse(**t) for t in templates]
    )


@router.post("/transform")
async def transform_cv(
    db: DbSession,
    app_settings: AppSettings,
    file: UploadFile = File(...),
    template_name: str = Form(...),
    authorization: str = Header(default=""),
):
    """Transform a CV file into a standardized Word document.

    Upload a PDF or DOCX file and receive a formatted Word document back.
    """
    user_id = await require_transformer_access(db, authorization)

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    file_lower = file.filename.lower()
    if not (file_lower.endswith(".pdf") or file_lower.endswith(".docx")):
        raise HTTPException(
            status_code=400,
            detail="Format de fichier non supporté. Utilisez PDF ou DOCX",
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Maximum {MAX_FILE_SIZE // (1024*1024)} Mo",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # Check Gemini API key
    if not app_settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Service d'IA non configuré. Contactez l'administrateur.",
        )

    # Create services and use case (Dependency Injection with ports)
    template_repo = CvTemplateRepository(db)
    log_repo = CvTransformationLogRepository(db)
    gemini_client = GeminiClient(app_settings)
    docx_generator = DocxGenerator()
    pdf_extractor = PdfTextExtractor()
    docx_extractor = DocxTextExtractor()

    use_case = TransformCvUseCase(
        template_repository=template_repo,
        log_repository=log_repo,
        data_extractor=gemini_client,
        document_generator=docx_generator,
        pdf_text_extractor=pdf_extractor,
        docx_text_extractor=docx_extractor,
    )

    try:
        print(f"[CV Transform] Starting transformation: template={template_name}, file={file.filename}, size={len(content)}")
        output_content = await use_case.execute(
            user_id=user_id,
            template_name=template_name,
            file_content=content,
            filename=file.filename,
        )
        print(f"[CV Transform] Success: generated {len(output_content)} bytes")

        # Generate output filename
        original_name = file.filename.rsplit(".", 1)[0]
        output_filename = f"{original_name}_formatted.docx"

        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(output_content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
            },
        )

    except ValueError as e:
        print(f"[CV Transform] ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[CV Transform] Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la transformation: {str(e)}",
        )


@router.post("/templates/{template_name}", response_model=TemplateResponse)
async def upload_template(
    template_name: str,
    db: DbSession,
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    authorization: str = Header(default=""),
):
    """Upload or update a CV template (admin only).

    The template_name is a unique identifier (e.g., "gemini", "craftmania").
    """
    await require_admin(db, authorization)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Le template doit être un fichier .docx",
        )

    # Read file content
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # Validate template name
    template_name = template_name.lower().strip()
    if not template_name or len(template_name) > 50:
        raise HTTPException(
            status_code=400,
            detail="Nom de template invalide (1-50 caractères)",
        )

    template_repo = CvTemplateRepository(db)
    use_case = UploadTemplateUseCase(template_repo)

    try:
        result = await use_case.execute(
            name=template_name,
            display_name=display_name,
            file_content=content,
            file_name=file.filename,
            description=description,
        )
        return TemplateResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload: {str(e)}",
        )


@router.get("/stats", response_model=TransformationStatsResponse)
async def get_transformation_stats(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get CV transformation statistics (admin only)."""
    await require_admin(db, authorization)

    log_repo = CvTransformationLogRepository(db)
    use_case = GetTransformationStatsUseCase(log_repo)

    stats = await use_case.execute()
    return TransformationStatsResponse(**stats)
