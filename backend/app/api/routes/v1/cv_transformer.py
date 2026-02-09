"""CV Transformer API endpoints."""

import io
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.middleware.rate_limiter import limiter
from app.application.use_cases.cv_transformer import (
    GetTemplatesUseCase,
    GetTransformationStatsUseCase,
    TransformCvUseCase,
    UploadTemplateUseCase,
)
from app.dependencies import AppSettings, AppSettingsSvc, DbSession
from app.domain.value_objects import UserRole
from app.infrastructure.audit import audit_logger
from app.infrastructure.cv_transformer import (
    AnthropicClient,
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
    description: str | None = None
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

    return TemplatesListResponse(templates=[TemplateResponse(**t) for t in templates])


@router.post("/transform")
@limiter.limit("10/hour")
async def transform_cv(
    request: Request,
    db: DbSession,
    app_settings: AppSettings,
    app_settings_svc: AppSettingsSvc,
    file: UploadFile = File(...),
    template_name: str = Form(...),
    authorization: str = Header(default=""),
):
    """Transform a CV file into a standardized Word document.

    Upload a PDF or DOCX file and receive a formatted Word document back.
    Rate limited to 10 transformations per hour (expensive operation).
    """
    print(
        f"[CV Transform] Request received: template={template_name}, filename={file.filename}",
        flush=True,
    )

    user_id = await require_transformer_access(db, authorization)
    ip_address = request.client.host if request.client else None
    print(f"[CV Transform] User authenticated: {user_id}", flush=True)

    # Get AI provider and model from database settings
    cv_provider = await app_settings_svc.get_cv_ai_provider()

    if cv_provider == "claude":
        if not app_settings.ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Clé API Anthropic non configurée. Contactez l'administrateur.",
            )
        ai_model = await app_settings_svc.get_cv_ai_model_claude()
        data_extractor = AnthropicClient(app_settings)
    else:
        if not app_settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Clé API Gemini non configurée. Contactez l'administrateur.",
            )
        ai_model = await app_settings_svc.get_gemini_model_cv()
        data_extractor = GeminiClient(app_settings)

    print(f"[CV Transform] Using provider: {cv_provider}, model: {ai_model}", flush=True)

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
            detail=f"Fichier trop volumineux. Maximum {MAX_FILE_SIZE // (1024 * 1024)} Mo",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # Create services and use case (Dependency Injection with ports)
    template_repo = CvTemplateRepository(db)
    log_repo = CvTransformationLogRepository(db)
    docx_generator = DocxGenerator()
    pdf_extractor = PdfTextExtractor()
    docx_extractor = DocxTextExtractor()

    use_case = TransformCvUseCase(
        template_repository=template_repo,
        log_repository=log_repo,
        data_extractor=data_extractor,
        document_generator=docx_generator,
        pdf_text_extractor=pdf_extractor,
        docx_text_extractor=docx_extractor,
    )

    try:
        print(
            f"[CV Transform] Starting transformation: template={template_name}, file={file.filename}, size={len(content)}",
            flush=True,
        )
        output_content = await use_case.execute(
            user_id=user_id,
            template_name=template_name,
            file_content=content,
            filename=file.filename,
            gemini_model=ai_model,
        )
        print(f"[CV Transform] Success: generated {len(output_content)} bytes", flush=True)

        # Audit log successful transformation
        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template=template_name,
            success=True,
            ip_address=ip_address,
        )

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
        print(f"[CV Transform] ValueError: {str(e)}", flush=True)
        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template=template_name,
            success=False,
            ip_address=ip_address,
            error_message=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[CV Transform] Exception: {type(e).__name__}: {str(e)}", flush=True)
        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template=template_name,
            success=False,
            ip_address=ip_address,
            error_message=str(e),
        )
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
    description: str | None = Form(None),
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


class GeminiTestResponse(BaseModel):
    """Gemini API test response."""

    success: bool
    message: str
    api_key_configured: bool


@router.get("/test-gemini", response_model=GeminiTestResponse)
async def test_gemini_api(
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Test Gemini API connectivity (admin only)."""
    await require_admin(db, authorization)

    # Check if API key is configured
    if not app_settings.GEMINI_API_KEY:
        return GeminiTestResponse(
            success=False,
            message="GEMINI_API_KEY non configurée",
            api_key_configured=False,
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=app_settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # Simple test prompt
        response = model.generate_content("Réponds uniquement 'OK' si tu fonctionnes.")

        if response.text:
            return GeminiTestResponse(
                success=True,
                message=f"Gemini fonctionne. Réponse: {response.text.strip()[:100]}",
                api_key_configured=True,
            )
        else:
            return GeminiTestResponse(
                success=False,
                message="Réponse vide de Gemini",
                api_key_configured=True,
            )

    except Exception as e:
        return GeminiTestResponse(
            success=False,
            message=f"Erreur Gemini: {str(e)}",
            api_key_configured=True,
        )
