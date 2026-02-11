"""CV Generator (Beta) API endpoint.

Returns parsed JSON to the frontend for client-side DOCX generation.
Supports SSE streaming for progressive feedback.
"""

import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
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

    # Get Claude model from Beta-specific settings
    ai_model = await app_settings_svc.get_cv_generator_beta_model()

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
        logger.info(f"[CV Generator] Parsing: file={file.filename}, model={ai_model}")
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


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/parse-stream")
@limiter.limit("10/hour")
async def parse_cv_stream(
    request: Request,
    db: DbSession,
    app_settings: AppSettings,
    app_settings_svc: AppSettingsSvc,
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    """Upload a CV and get parsed JSON via SSE streaming with progress updates.

    Sends Server-Sent Events:
    - event: progress  {step, message, percent}
    - event: complete  {success, data, model_used}
    - event: error     {message}
    """
    # Authenticate before streaming
    user_id = await _require_access(db, authorization)
    ip_address = request.client.host if request.client else None

    if not app_settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Clé API Anthropic non configurée. Contactez l'administrateur.",
        )

    ai_model = await app_settings_svc.get_cv_generator_beta_model()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    file_lower = file.filename.lower()
    if not (file_lower.endswith(".pdf") or file_lower.endswith(".docx")):
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez PDF ou DOCX.",
        )

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Maximum {MAX_FILE_SIZE // (1024 * 1024)} Mo",
        )

    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    filename = file.filename

    async def event_stream() -> AsyncGenerator[str, None]:
        """Generate SSE events for CV parsing progress."""
        try:
            # Step 1: Extracting text
            yield _sse_event("progress", {
                "step": "extracting",
                "message": "Extraction du texte du document...",
                "percent": 10,
            })

            try:
                if file_lower.endswith(".pdf"):
                    extractor = PdfTextExtractor()
                    cv_text = extractor.extract(file_content)
                else:
                    extractor = DocxTextExtractor()
                    cv_text = extractor.extract(file_content)
            except Exception as e:
                yield _sse_event("error", {"message": f"Erreur d'extraction du texte: {str(e)}"})
                return

            yield _sse_event("progress", {
                "step": "extracting",
                "message": "Texte extrait avec succès",
                "percent": 20,
            })

            # Step 2: AI Parsing
            yield _sse_event("progress", {
                "step": "ai_parsing",
                "message": "Analyse IA en cours (Claude)...",
                "percent": 30,
            })

            parser = CvGeneratorParser(app_settings)
            log_repo = CvTransformationLogRepository(db)

            try:
                logger.info(f"[CV Generator SSE] Parsing: file={filename}, model={ai_model}")
                cv_data = await parser.parse_cv(cv_text, model_name=ai_model)
            except (ValueError, Exception) as e:
                logger.warning(f"[CV Generator SSE] Error: {type(e).__name__}: {str(e)}")

                from app.domain.entities.cv_transformation_log import CvTransformationLog

                log = CvTransformationLog.create_failure(
                    user_id=user_id,
                    template_name="cv-generator-beta",
                    original_filename=filename,
                    error_message=str(e),
                )
                await log_repo.save(log)

                audit_logger.log_cv_transform(
                    user_id=user_id,
                    filename=filename,
                    template="cv-generator-beta",
                    success=False,
                    ip_address=ip_address,
                    error_message=str(e),
                )
                yield _sse_event("error", {"message": str(e)})
                return

            yield _sse_event("progress", {
                "step": "ai_parsing",
                "message": "Analyse IA terminée",
                "percent": 85,
            })

            # Step 3: Validation
            yield _sse_event("progress", {
                "step": "validating",
                "message": "Validation des données...",
                "percent": 90,
            })

            # Log success
            from app.domain.entities.cv_transformation_log import CvTransformationLog

            log = CvTransformationLog.create_success(
                user_id=user_id,
                template_name="cv-generator-beta",
                original_filename=filename,
            )
            await log_repo.save(log)

            audit_logger.log_cv_transform(
                user_id=user_id,
                filename=filename,
                template="cv-generator-beta",
                success=True,
                ip_address=ip_address,
            )

            # Step 4: Complete
            yield _sse_event("progress", {
                "step": "complete",
                "message": "CV parsé avec succès !",
                "percent": 100,
            })

            yield _sse_event("complete", {
                "success": True,
                "data": cv_data,
                "model_used": ai_model,
            })

        except Exception as e:
            logger.error(f"[CV Generator SSE] Unexpected error: {type(e).__name__}: {str(e)}")
            yield _sse_event("error", {"message": f"Erreur inattendue: {str(e)}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
