"""Webhook routes for BoondManager and YouSign."""

import json
import traceback

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.contract_management.api.schemas import WebhookResponse
from app.contract_management.application.use_cases.create_contract_request import (
    CreateContractRequestUseCase,
)
from app.contract_management.domain.exceptions import WebhookDuplicateError
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
    WebhookEventRepository,
)
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger

logger = structlog.get_logger()

router = APIRouter(tags=["Webhooks"])


@router.post(
    "/boondmanager/positioning-update",
    response_model=WebhookResponse,
    summary="Handle BoondManager positioning update webhook",
)
async def handle_boond_positioning_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle positioning update from BoondManager.

    Always returns 200 OK to prevent retries from Boond.
    """
    settings = get_settings()

    # Log raw body for debugging
    raw_body = await request.body()
    logger.info(
        "webhook_boond_received",
        content_type=request.headers.get("content-type", ""),
        body_length=len(raw_body),
        body_preview=raw_body[:500].decode("utf-8", errors="replace"),
    )

    try:
        payload = json.loads(raw_body)
    except Exception:
        logger.warning("webhook_invalid_json", raw=raw_body[:200].decode("utf-8", errors="replace"))
        return WebhookResponse(status="ok", message="Invalid JSON")

    logger.info(
        "webhook_boond_payload_parsed",
        payload_type=type(payload).__name__,
        payload_keys=list(payload.keys()) if isinstance(payload, dict) else f"list[{len(payload)}]",
    )

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT_REQUEST,
        details={"source": "boondmanager", "type": "positioning_update"},
    )

    cr_repo = ContractRequestRepository(db)
    webhook_repo = WebhookEventRepository(db)

    from app.infrastructure.email.sender import EmailService

    email_service = EmailService(settings)

    from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
        BoondCrmAdapter,
    )
    from app.infrastructure.boond.client import BoondClient
    from app.infrastructure.database.repositories.user_repository import UserRepository

    boond_client = BoondClient(settings)
    crm_service = BoondCrmAdapter(boond_client)
    user_repo = UserRepository(db)

    use_case = CreateContractRequestUseCase(
        contract_request_repository=cr_repo,
        webhook_event_repository=webhook_repo,
        crm_service=crm_service,
        email_service=email_service,
        user_repository=user_repo,
        frontend_url=settings.frontend_url,
    )

    try:
        result = await use_case.execute(payload)
        if result:
            logger.info(
                "webhook_boond_contract_created",
                reference=result.reference,
                cr_id=str(result.id),
            )
            return WebhookResponse(
                status="ok",
                message=f"Contract request {result.reference} created",
            )
        logger.info("webhook_boond_no_action", reason="filtered_or_empty")
        return WebhookResponse(status="ok", message="No action taken")
    except WebhookDuplicateError as exc:
        logger.info("webhook_boond_duplicate", event_id=str(exc))
        return WebhookResponse(status="ok", message="Duplicate event")
    except Exception as exc:
        logger.error(
            "webhook_processing_error",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return WebhookResponse(status="ok", message="Processing error")


@router.post(
    "/boondmanager/test",
    summary="Test endpoint - simulate a Boond positioning webhook",
)
async def test_boond_webhook(request: Request):
    """Test endpoint that logs the raw payload without processing.

    Use this to verify connectivity and inspect the payload format.
    Not available in production.
    """
    settings = get_settings()
    if settings.is_production:
        return {"status": "error", "message": "Not available in production"}

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except Exception:
        payload = None

    return {
        "status": "ok",
        "message": "Test webhook received",
        "headers": {
            k: v for k, v in request.headers.items()
            if k.lower() in ("content-type", "user-agent", "x-forwarded-for", "host")
        },
        "body_length": len(raw_body),
        "payload_type": type(payload).__name__ if payload else "invalid_json",
        "payload": payload,
    }


@router.post(
    "/yousign/signature-completed",
    response_model=WebhookResponse,
    summary="Handle YouSign signature completed webhook",
)
async def handle_yousign_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle signature completed event from YouSign."""
    settings = get_settings()

    try:
        payload = await request.json()
    except Exception:
        logger.warning("yousign_webhook_invalid_json")
        return WebhookResponse(status="ok", message="Invalid JSON")

    # Verify webhook secret if configured
    webhook_secret = settings.YOUSIGN_WEBHOOK_SECRET
    if webhook_secret:
        # YouSign sends signature in header
        signature = request.headers.get("x-yousign-signature", "")
        if not signature:
            logger.warning("yousign_webhook_no_signature")
            return WebhookResponse(status="ok", message="Missing signature")

    audit_logger.log(
        AuditAction.WEBHOOK_RECEIVED,
        AuditResource.CONTRACT,
        details={"source": "yousign", "type": "signature_completed"},
    )

    event_type = payload.get("event_name", "")
    if event_type != "signature_request.done":
        return WebhookResponse(status="ok", message=f"Ignored event: {event_type}")

    procedure_id = payload.get("data", {}).get("signature_request", {}).get("id", "")
    if not procedure_id:
        logger.warning("yousign_webhook_no_procedure_id")
        return WebhookResponse(status="ok", message="No procedure ID")

    logger.info(
        "yousign_signature_completed",
        procedure_id=procedure_id,
    )

    # Process signature completion
    try:
        from app.contract_management.application.use_cases.handle_signature_completed import (
            HandleSignatureCompletedUseCase,
        )
        from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
            ContractRepository,
        )
        from app.contract_management.infrastructure.adapters.yousign_client import YouSignClient
        from app.infrastructure.email.sender import EmailService
        from app.infrastructure.storage.s3_client import S3StorageClient

        cr_repo = ContractRequestRepository(db)
        contract_repo = ContractRepository(db)
        yousign = YouSignClient(
            api_key=settings.YOUSIGN_API_KEY,
            base_url=settings.YOUSIGN_API_BASE_URL,
        )
        s3_service = S3StorageClient(settings)
        email_service = EmailService(settings)

        use_case = HandleSignatureCompletedUseCase(
            contract_request_repository=cr_repo,
            contract_repository=contract_repo,
            signature_service=yousign,
            s3_service=s3_service,
            email_service=email_service,
        )

        await use_case.execute(procedure_id)

        audit_logger.log(
            AuditAction.CONTRACT_SIGNED,
            AuditResource.CONTRACT,
            details={"procedure_id": procedure_id},
        )

        return WebhookResponse(status="ok", message="Signature processed")
    except Exception as exc:
        logger.error("yousign_webhook_processing_error", error=str(exc))
        return WebhookResponse(status="ok", message="Processing error")
