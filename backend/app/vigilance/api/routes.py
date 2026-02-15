"""Vigilance API routes for ADV/admin."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser
from app.config import get_settings
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.infrastructure.database.connection import get_db
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
)
from app.vigilance.application.use_cases.reject_document import RejectDocumentUseCase
from app.vigilance.application.use_cases.request_documents import RequestDocumentsUseCase
from app.vigilance.application.use_cases.validate_document import ValidateDocumentUseCase
from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository

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
        auto_check_results=doc.auto_check_results,
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
        siren=tp.siren,
        type=tp.type.value,
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
    db: AsyncSession = Depends(get_db),
):
    """Create document requests based on third party type. ADV/admin only."""
    tp_repo = ThirdPartyRepository(db)
    doc_repo = DocumentRepository(db)

    use_case = RequestDocumentsUseCase(
        third_party_repository=tp_repo,
        document_repository=doc_repo,
    )

    try:
        created = await use_case.execute(third_party_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_document_to_response(d) for d in created]


@router.post(
    "/documents/{document_id}/validate",
    response_model=DocumentResponse,
    summary="Validate a document",
)
async def validate_document(
    document_id: UUID,
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
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

    use_case = RejectDocumentUseCase(
        document_repository=doc_repo,
        third_party_repository=tp_repo,
        email_service=email_service,
        portal_base_url=settings.BOBBY_PORTAL_BASE_URL,
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
