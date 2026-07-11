"""Vigilance API routes for ADV/admin."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser
from app.config import get_settings
from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.infrastructure.storage.s3_client import S3StorageClient
from app.third_party.api.schemas import (
    ThirdPartyListResponse,
    ThirdPartyResponse,
)
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)
from app.vigilance.api.schemas import (
    DocumentResponse,
    RejectDocumentRequest,
    ThirdPartyWithDocumentsResponse,
    ValidateDocumentRequest,
)
from app.vigilance.application.use_cases.reject_document import RejectDocumentUseCase
from app.vigilance.application.use_cases.request_documents import RequestDocumentsUseCase
from app.vigilance.application.use_cases.validate_document import ValidateDocumentUseCase
from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository
from app.vigilance.infrastructure.adapters.s3_document_storage import VigilanceDocumentStorage

logger = structlog.get_logger()

router = APIRouter(tags=["Vigilance"])


def _document_to_response(doc) -> DocumentResponse:
    """Convert a VigilanceDocument entity to a response."""
    return DocumentResponse(
        id=doc.id,
        third_party_id=doc.third_party_id,
        document_type=doc.document_type.value,
        document_type_display=doc.document_type.display_name,
        status=doc.status.value,
        s3_key=doc.s3_key,
        file_name=doc.file_name,
        file_size=doc.file_size,
        uploaded_at=doc.uploaded_at,
        validated_at=doc.validated_at,
        validated_by=doc.validated_by,
        rejected_at=doc.rejected_at,
        rejection_reason=doc.rejection_reason,
        expires_at=doc.expires_at,
        document_date=doc.document_date,
        is_valid_at_upload=doc.is_valid_at_upload,
        auto_check_results=doc.auto_check_results,
        is_unavailable=doc.is_unavailable,
        unavailability_reason=doc.unavailability_reason,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get(
    "/third-parties",
    response_model=ThirdPartyListResponse,
    summary="List third parties with compliance status",
)
async def list_third_parties(
    user_id: AdvOrAdminUser,
    skip: int = 0,
    limit: int = 50,
    compliance_status: str | None = None,
    search: str | None = None,
    third_party_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List third parties with optional filters. ADV/admin only."""
    from app.third_party.domain.value_objects.compliance_status import ComplianceStatus

    tp_repo = ThirdPartyRepository(db)

    status_filter = None
    if compliance_status:
        try:
            status_filter = ComplianceStatus(compliance_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut de conformité invalide : {compliance_status}",
            )

    items = await tp_repo.list_all(
        skip=skip,
        limit=limit,
        compliance_status=status_filter,
        search=search,
        third_party_type=third_party_type,
    )
    total = await tp_repo.count(
        compliance_status=status_filter,
        search=search,
        third_party_type=third_party_type,
    )

    return ThirdPartyListResponse(
        items=[
            ThirdPartyResponse(
                id=tp.id,
                boond_provider_id=tp.boond_provider_id,
                type=tp.type.value,
                company_name=tp.company_name,
                legal_form=tp.legal_form,
                capital=tp.capital,
                siren=tp.siren,
                siret=tp.siret,
                rcs_city=tp.rcs_city,
                rcs_number=tp.rcs_number,
                head_office_address=tp.head_office_address,
                representative_name=tp.representative_name,
                representative_title=tp.representative_title,
                contact_email=tp.contact_email,
                compliance_status=tp.compliance_status.value,
                created_at=tp.created_at,
                updated_at=tp.updated_at,
            )
            for tp in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/third-parties/{third_party_id}/documents",
    response_model=ThirdPartyWithDocumentsResponse,
    summary="Get third party with documents",
)
async def get_third_party_documents(
    third_party_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a third party with all its documents. ADV/admin only."""
    tp_repo = ThirdPartyRepository(db)
    doc_repo = DocumentRepository(db)

    tp = await tp_repo.get_by_id(third_party_id)
    if not tp:
        raise HTTPException(status_code=404, detail="Tiers non trouvé.")

    documents = await doc_repo.list_by_third_party(third_party_id)
    counts = await doc_repo.count_by_status(third_party_id)

    return ThirdPartyWithDocumentsResponse(
        id=tp.id,
        company_name=tp.company_name,
        legal_form=tp.legal_form,
        capital=tp.capital,
        siren=tp.siren,
        siret=tp.siret,
        vat_number=tp.vat_number,
        ape_code=tp.ape_code,
        rcs_city=tp.rcs_city,
        rcs_number=tp.rcs_number,
        head_office_address=tp.head_office_address,
        head_office_street=tp.head_office_street,
        head_office_postal_code=tp.head_office_postal_code,
        head_office_city=tp.head_office_city,
        representative_name=tp.representative_name,
        representative_title=tp.representative_title,
        representative_civility=tp.representative_civility,
        representative_first_name=tp.representative_first_name,
        representative_last_name=tp.representative_last_name,
        representative_email=tp.representative_email,
        representative_phone=tp.representative_phone,
        signatory_civility=tp.signatory_civility,
        signatory_first_name=tp.signatory_first_name,
        signatory_last_name=tp.signatory_last_name,
        signatory_email=tp.signatory_email,
        signatory_phone=tp.signatory_phone,
        signatory_is_director=tp.signatory_is_director,
        adv_contact_civility=tp.adv_contact_civility,
        adv_contact_first_name=tp.adv_contact_first_name,
        adv_contact_last_name=tp.adv_contact_last_name,
        adv_contact_email=tp.adv_contact_email,
        adv_contact_phone=tp.adv_contact_phone,
        billing_contact_civility=tp.billing_contact_civility,
        billing_contact_first_name=tp.billing_contact_first_name,
        billing_contact_last_name=tp.billing_contact_last_name,
        billing_contact_email=tp.billing_contact_email,
        billing_contact_phone=tp.billing_contact_phone,
        type=tp.type.value,
        entity_category=tp.entity_category,
        company_info_submitted=tp.company_info_submitted,
        compliance_status=tp.compliance_status.value,
        contact_email=tp.contact_email,
        documents=[_document_to_response(d) for d in documents],
        document_counts=counts,
    )


@router.post(
    "/third-parties/{third_party_id}/request-documents",
    response_model=list[DocumentResponse],
    summary="Request documents for a third party",
)
async def request_documents(
    third_party_id: UUID,
    user_id: AdvOrAdminUser,
    entity_category: str = Query(..., pattern="^(ei|societe)$", description="ei ou societe"),
    db: AsyncSession = Depends(get_db),
):
    """Create document requests based on entity category. ADV/admin only."""
    tp_repo = ThirdPartyRepository(db)
    doc_repo = DocumentRepository(db)

    use_case = RequestDocumentsUseCase(
        third_party_repository=tp_repo,
        document_repository=doc_repo,
    )

    try:
        created = await use_case.execute(third_party_id, entity_category=entity_category)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_document_to_response(d) for d in created]


@router.post(
    "/documents/{document_id}/upload",
    response_model=DocumentResponse,
    summary="Upload a document internally (ADV/admin, on behalf of the tiers)",
)
async def upload_document_internal(
    document_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Upload a vigilance document file on behalf of the tiers. ADV/admin only.

    Mirrors the portal upload (type/extension allowlist + size guard + Gemini
    auto-extraction) but authenticated by JWT instead of a magic link, so an ADV
    can constitute the whole compliance dossier manually without soliciting the
    tiers. The document still needs to be validated afterwards (existing
    `/documents/{id}/validate`).
    """
    import os

    from app.vigilance.application.use_cases.upload_document import (
        UploadDocumentCommand,
        UploadDocumentUseCase,
    )
    from app.vigilance.domain.exceptions import (
        DocumentNotAllowedError,
        DocumentNotFoundError,
        ExpiredDocumentError,
        InvalidDocumentTransitionError,
    )
    from app.vigilance.domain.services.vigilance_requirements import (
        ALLOWED_EXTENSIONS,
        ALLOWED_MIME_TYPES,
        MAX_FILE_SIZE_BYTES,
    )
    from app.vigilance.infrastructure.adapters.gemini_document_extractor import (
        GeminiDocumentExtractor,
    )

    settings = get_settings()
    doc_repo = DocumentRepository(db)

    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    # Same hardening as the public portal: allowlist type/extension + size cap
    # BEFORE any heavy processing (full read, S3 upload, Gemini extraction).
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Format de fichier non autorisé. Formats acceptés : PDF, JPG, PNG.",
        )
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Extension de fichier non autorisée. Extensions acceptées : .pdf, .jpg, .jpeg, .png.",
        )

    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (maximum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} Mo).",
        )

    storage = VigilanceDocumentStorage(S3StorageClient(settings))
    extractor = GeminiDocumentExtractor(settings)
    use_case = UploadDocumentUseCase(
        document_repository=doc_repo,
        document_storage=storage,
        document_extractor=extractor,
    )

    try:
        updated = await use_case.execute(
            UploadDocumentCommand(
                document_id=document_id,
                file_content=file_content,
                file_name=file.filename or "document.pdf",
                content_type=file.content_type or "application/octet-stream",
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DocumentNotAllowedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ExpiredDocumentError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except InvalidDocumentTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    audit_logger.log(
        AuditAction.DOCUMENT_UPLOADED,
        AuditResource.VIGILANCE_DOCUMENT,
        user_id=user_id,
        resource_id=str(updated.id),
        details={
            "third_party_id": str(updated.third_party_id),
            "document_type": updated.document_type.value,
            "file_name": file.filename,
            "via": "adv_internal",
        },
    )

    return _document_to_response(updated)


@router.get(
    "/documents/{document_id}/download-url",
    summary="Get presigned download URL for a vigilance document",
)
async def get_document_download_url(
    document_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate a presigned S3 URL to view/download a vigilance document."""
    settings = get_settings()
    doc_repo = DocumentRepository(db)

    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé.")
    if not doc.s3_key:
        raise HTTPException(status_code=404, detail="Aucun fichier associé à ce document.")

    storage = VigilanceDocumentStorage(S3StorageClient(settings))
    url = await storage.get_download_url(doc.s3_key, expires_in=1800)
    return {"url": url, "file_name": doc.file_name}


@router.post(
    "/documents/{document_id}/validate",
    response_model=DocumentResponse,
    summary="Validate a document",
)
async def validate_document(
    document_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
    body: ValidateDocumentRequest | None = None,
):
    """Validate a received document. ADV/admin only."""
    doc_repo = DocumentRepository(db)
    tp_repo = ThirdPartyRepository(db)

    use_case = ValidateDocumentUseCase(
        document_repository=doc_repo,
        third_party_repository=tp_repo,
    )

    try:
        doc = await use_case.execute(
            document_id=document_id,
            validated_by=str(user_id),
            document_date=body.document_date if body else None,
            expires_at_override=body.expires_at if body else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.DOCUMENT_VALIDATED,
        AuditResource.VIGILANCE_DOCUMENT,
        user_id=user_id,
        resource_id=str(document_id),
    )

    return _document_to_response(doc)


@router.post(
    "/documents/{document_id}/reject",
    response_model=DocumentResponse,
    summary="Reject a document",
)
async def reject_document(
    document_id: UUID,
    body: RejectDocumentRequest,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Reject a received document with reason. ADV/admin only."""
    settings = get_settings()
    doc_repo = DocumentRepository(db)
    tp_repo = ThirdPartyRepository(db)

    from app.infrastructure.email.sender import EmailService

    email_service = EmailService(settings)

    async def _resolve_company_email_for_tp(third_party_id):
        from sqlalchemy import select

        from app.contract_management.infrastructure.models import (
            ContractCompanyModel,
            ContractRequestModel,
        )

        cr_result = await db.execute(
            select(ContractRequestModel.company_id)
            .where(ContractRequestModel.third_party_id == third_party_id)
            .order_by(ContractRequestModel.created_at.desc())
            .limit(1)
        )
        company_id = cr_result.scalar_one_or_none()
        if not company_id:
            return None, None
        c_result = await db.execute(
            select(ContractCompanyModel.email_from, ContractCompanyModel.name).where(
                ContractCompanyModel.id == company_id
            )
        )
        row = c_result.first()
        return (row.email_from, row.name) if row else (None, None)

    use_case = RejectDocumentUseCase(
        document_repository=doc_repo,
        third_party_repository=tp_repo,
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
        company_email_resolver=_resolve_company_email_for_tp,
    )

    try:
        doc = await use_case.execute(
            document_id=document_id,
            reason=body.reason,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit_logger.log(
        AuditAction.DOCUMENT_REJECTED,
        AuditResource.VIGILANCE_DOCUMENT,
        user_id=user_id,
        resource_id=str(document_id),
        details={"reason": body.reason},
    )

    return _document_to_response(doc)


# ── Manual edit & re-extraction ───────────────────────────────────────────────


@router.patch(
    "/documents/{document_id}/auto-check",
    response_model=DocumentResponse,
    summary="Edit auto-check results for a document",
)
async def update_auto_check(
    document_id: UUID,
    body: dict,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Manually edit the auto-check extraction results (beneficiaire, IBAN, BIC, dates). ADV/admin only."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    existing = doc.auto_check_results or {}
    existing.update(body)
    doc.auto_check_results = existing
    doc.updated_at = __import__("datetime").datetime.utcnow()
    saved = await doc_repo.save(doc)

    audit_logger.log(
        AuditAction.DOCUMENT_VALIDATED,
        AuditResource.VIGILANCE_DOCUMENT,
        user_id=user_id,
        resource_id=str(document_id),
        details={"action": "auto_check_updated", "fields": list(body.keys())},
    )

    return _document_to_response(saved)


@router.post(
    "/documents/{document_id}/re-extract",
    response_model=DocumentResponse,
    summary="Re-run auto extraction on a document",
)
async def re_extract_document(
    document_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Re-run the auto extraction on an uploaded document. ADV/admin only."""
    settings = get_settings()
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if not doc.s3_key:
        raise HTTPException(status_code=400, detail="Aucun fichier associe.")

    s3 = S3StorageClient(settings)
    try:
        file_content = await s3.download_file(doc.s3_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur S3: {exc}")

    from app.vigilance.infrastructure.adapters.gemini_document_extractor import DocumentExtractor

    extractor = DocumentExtractor(settings)
    content_type = "application/pdf" if doc.s3_key.endswith(".pdf") else "application/octet-stream"
    extracted = await extractor.extract(doc.document_type.value, file_content, content_type)

    if extracted:
        doc.auto_check_results = extracted
        from datetime import date, datetime

        doc_date_str = extracted.get("document_date")
        if doc_date_str:
            try:
                doc.document_date = date.fromisoformat(doc_date_str)
            except ValueError:
                pass
        expiry_date_str = extracted.get("expiry_date")
        if expiry_date_str:
            try:
                expiry_d = date.fromisoformat(expiry_date_str)
                doc.expires_at = datetime(expiry_d.year, expiry_d.month, expiry_d.day)
            except ValueError:
                pass
        is_valid = extracted.get("is_valid")
        if is_valid is not None:
            doc.is_valid_at_upload = bool(is_valid)

    doc.updated_at = __import__("datetime").datetime.utcnow()
    saved = await doc_repo.save(doc)

    audit_logger.log(
        AuditAction.DOCUMENT_VALIDATED,
        AuditResource.VIGILANCE_DOCUMENT,
        user_id=user_id,
        resource_id=str(document_id),
        details={"action": "re_extracted", "results": extracted},
    )

    return _document_to_response(saved)
