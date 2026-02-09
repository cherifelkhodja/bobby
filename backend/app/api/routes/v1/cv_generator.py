"""CV Generator (Beta) API endpoint.

Returns parsed JSON to the frontend for client-side DOCX generation.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.api.middleware.rate_limiter import limiter
from app.dependencies import AppSettings, AppSettingsSvc, DbSession
from app.domain.value_objects import UserRole
from app.infrastructure.audit import audit_logger
from app.infrastructure.cv_generator import CvGeneratorParser
from app.infrastructure.cv_transformer import DocxTextExtractor, PdfTextExtractor
from app.infrastructure.database.repositories import (
    CvTransformationLogRepository,
    UserRepository,
)
from app.infrastructure.security.jwt import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_ROLES = {UserRole.ADMIN, UserRole.COMMERCIAL, UserRole.RH}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB


class CvGeneratorParseResponse(BaseModel):
    """Response from CV Generator parse endpoint."""

    success: bool
    data: dict
    model_used: str


async def _require_access(db: DbSession, authorization: str) -> UUID:
    """Verify user has access (admin, commercial, or rh)."""
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
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux administrateurs, commerciaux et RH",
        )

    return user_id


@router.post("/parse", response_model=CvGeneratorParseResponse)
@limiter.limit("10/hour")
async def parse_cv(
    request: Request,
    db: DbSession,
    app_settings: AppSettings,
    app_settings_svc: AppSettingsSvc,
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    """Upload a CV file and get parsed section-based JSON.

    The JSON is designed for frontend DOCX generation using docx-js.
    Rate limited to 10 requests per hour (expensive AI operation).
    """
    user_id = await _require_access(db, authorization)
    ip_address = request.client.host if request.client else None

    # Validate API key
    if not app_settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Clé API Anthropic non configurée. Contactez l'administrateur.",
        )

    # Get Claude model from settings
    ai_model = await app_settings_svc.get_cv_ai_model_claude()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    file_lower = file.filename.lower()
    if not (file_lower.endswith(".pdf") or file_lower.endswith(".docx")):
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez PDF ou DOCX.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Maximum {MAX_FILE_SIZE // (1024 * 1024)} Mo",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # Extract text
    try:
        if file_lower.endswith(".pdf"):
            extractor = PdfTextExtractor()
            cv_text = extractor.extract(content)
        else:
            extractor = DocxTextExtractor()
            cv_text = extractor.extract(content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erreur d'extraction du texte: {str(e)}",
        )

    # Parse with Claude
    parser = CvGeneratorParser(app_settings)
    log_repo = CvTransformationLogRepository(db)

    try:
        logger.info(
            f"[CV Generator] Parsing: file={file.filename}, model={ai_model}"
        )
        cv_data = await parser.parse_cv(cv_text, model_name=ai_model)

        # Log success
        from app.domain.entities.cv_transformation_log import CvTransformationLog

        log = CvTransformationLog.create_success(
            user_id=user_id,
            template_name="cv-generator-beta",
            original_filename=file.filename,
        )
        await log_repo.save(log)

        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template="cv-generator-beta",
            success=True,
            ip_address=ip_address,
        )

        return CvGeneratorParseResponse(
            success=True,
            data=cv_data,
            model_used=ai_model,
        )

    except ValueError as e:
        logger.warning(f"[CV Generator] ValueError: {str(e)}")

        from app.domain.entities.cv_transformation_log import CvTransformationLog

        log = CvTransformationLog.create_failure(
            user_id=user_id,
            template_name="cv-generator-beta",
            original_filename=file.filename,
            error_message=str(e),
        )
        await log_repo.save(log)

        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template="cv-generator-beta",
            success=False,
            ip_address=ip_address,
            error_message=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"[CV Generator] Error: {type(e).__name__}: {str(e)}")

        from app.domain.entities.cv_transformation_log import CvTransformationLog

        log = CvTransformationLog.create_failure(
            user_id=user_id,
            template_name="cv-generator-beta",
            original_filename=file.filename,
            error_message=str(e),
        )
        await log_repo.save(log)

        audit_logger.log_cv_transform(
            user_id=user_id,
            filename=file.filename,
            template="cv-generator-beta",
            success=False,
            ip_address=ip_address,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du parsing: {str(e)}",
        )
