"""Portal routes for third party magic link access."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.third_party.api.schemas import (
    ContractReviewRequest,
    ContractReviewResponse,
    DocumentUploadResponse,
    MagicLinkPortalResponse,
    PortalDocumentResponse,
    PortalDocumentsListResponse,
    ThirdPartyPortalResponse,
)
from app.third_party.application.use_cases.verify_magic_link import (
    VerifyMagicLinkUseCase,
)
from app.third_party.domain.exceptions import (
    MagicLinkExpiredError,
    MagicLinkNotFoundError,
    MagicLinkRevokedError,
)
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
    MagicLinkRepository,
)
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)
from app.vigilance.infrastructure.adapters.postgres_document_repo import (
    DocumentRepository,
)
from app.vigilance.infrastructure.adapters.s3_document_storage import (
    VigilanceDocumentStorage,
)

logger = structlog.get_logger()

router = APIRouter(tags=["Portal"])


@router.get(
    "/portal/{token}",
    response_model=MagicLinkPortalResponse,
    summary="Verify magic link and get portal info",
)
async def get_portal_info(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify a magic link token and return portal information.

    This is a public endpoint — no authentication required.
    The token itself acts as the authentication.
    """
    magic_link_repo = MagicLinkRepository(db)
    third_party_repo = ThirdPartyRepository(db)

    use_case = VerifyMagicLinkUseCase(
        magic_link_repository=magic_link_repo,
        third_party_repository=third_party_repo,
    )

    try:
        result = await use_case.execute(token)
    except MagicLinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien invalide ou introuvable.",
        )
    except MagicLinkRevokedError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Ce lien a été révoqué.",
        )
    except MagicLinkExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Ce lien a expiré.",
        )

    audit_logger.log(
        AuditAction.PORTAL_ACCESSED,
        AuditResource.MAGIC_LINK,
        resource_id=str(result.magic_link.id),
        details={
            "third_party_id": str(result.third_party.id),
            "purpose": result.purpose.value,
        },
    )

    return MagicLinkPortalResponse(
        third_party=ThirdPartyPortalResponse(
            id=result.third_party.id,
            company_name=result.third_party.company_name,
            contact_email=result.third_party.contact_email,
            compliance_status=result.third_party.compliance_status.value,
            type=result.third_party.type.value,
        ),
        purpose=result.purpose.value,
        contract_request_id=result.contract_request_id,
    )


# ── Portal Document Routes ──────────────────────────────────────


async def _verify_portal_token(
    token: str, db: AsyncSession, expected_purpose: MagicLinkPurpose | None = None
):
    """Verify a magic link token and return the result.

    Args:
        token: The magic link token.
        db: Database session.
        expected_purpose: If set, verify the purpose matches.

    Returns:
        The verification result.

    Raises:
        HTTPException: If the token is invalid.
    """
    magic_link_repo = MagicLinkRepository(db)
    third_party_repo = ThirdPartyRepository(db)
    use_case = VerifyMagicLinkUseCase(
        magic_link_repository=magic_link_repo,
        third_party_repository=third_party_repo,
    )
    try:
        result = await use_case.execute(token)
    except MagicLinkNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien invalide.")
    except MagicLinkRevokedError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Ce lien a été révoqué.")
    except MagicLinkExpiredError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Ce lien a expiré.")

    if expected_purpose and result.purpose != expected_purpose:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce lien ne permet pas cette action.",
        )
    return result


@router.get(
    "/portal/{token}/documents",
    response_model=PortalDocumentsListResponse,
    summary="List documents for a third party via portal",
)
async def get_portal_documents(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """List documents expected/uploaded for this third party."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    doc_repo = DocumentRepository(db)
    documents = await doc_repo.list_by_third_party(result.third_party.id)

    return PortalDocumentsListResponse(
        third_party_id=result.third_party.id,
        company_name=result.third_party.company_name,
        documents=[
            PortalDocumentResponse(
                id=doc.id,
                document_type=doc.document_type.value,
                status=doc.status.value,
                file_name=doc.file_name,
                uploaded_at=doc.uploaded_at,
                rejected_at=doc.rejected_at,
                rejection_reason=doc.rejection_reason,
            )
            for doc in documents
        ],
    )


@router.post(
    "/portal/{token}/documents/{document_id}/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document via portal",
)
async def upload_portal_document(
    token: str,
    document_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document file via the portal magic link."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    from app.vigilance.application.use_cases.upload_document import (
        UploadDocumentCommand,
        UploadDocumentUseCase,
    )

    doc_repo = DocumentRepository(db)
    storage = VigilanceDocumentStorage()

    # Verify the document belongs to this third party
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.third_party_id != result.third_party.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable.",
        )

    file_content = await file.read()
    use_case = UploadDocumentUseCase(
        document_repository=doc_repo,
        document_storage=storage,
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

    audit_logger.log(
        AuditAction.DOCUMENT_UPLOADED,
        AuditResource.VIGILANCE_DOCUMENT,
        resource_id=str(updated.id),
        details={
            "third_party_id": str(result.third_party.id),
            "document_type": updated.document_type.value,
            "file_name": file.filename,
            "via": "portal",
        },
    )

    return DocumentUploadResponse(
        document_id=updated.id,
        document_type=updated.document_type.value,
        status=updated.status.value,
        file_name=updated.file_name or "",
    )


# ── Portal Contract Review Routes ───────────────────────────────


@router.get(
    "/portal/{token}/contract-draft",
    summary="Get contract draft download URL via portal",
)
async def get_contract_draft(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the contract draft info for review."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.CONTRACT_REVIEW)

    if not result.contract_request_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune demande de contrat associée.",
        )

    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
    )

    contract_repo = ContractRepository(db)
    contracts = await contract_repo.list_by_contract_request(result.contract_request_id)
    if not contracts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun brouillon de contrat trouvé.",
        )

    contract = contracts[-1]
    return {
        "contract_id": str(contract.id),
        "reference": contract.reference,
        "version": contract.version,
        "s3_key_draft": contract.s3_key_draft,
        "contract_request_id": str(result.contract_request_id),
    }


@router.post(
    "/portal/{token}/contract-review",
    response_model=ContractReviewResponse,
    summary="Submit contract review decision via portal",
)
async def submit_contract_review(
    token: str,
    body: ContractReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Partner approves or requests changes on the contract draft."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.CONTRACT_REVIEW)

    if not result.contract_request_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune demande de contrat associée.",
        )

    from app.contract_management.application.use_cases.process_partner_review import (
        PartnerReviewCommand,
        ProcessPartnerReviewUseCase,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRequestRepository,
    )

    cr_repo = ContractRequestRepository(db)
    use_case = ProcessPartnerReviewUseCase(contract_request_repository=cr_repo)

    updated = await use_case.execute(
        PartnerReviewCommand(
            contract_request_id=result.contract_request_id,
            decision=body.decision,
            comments=body.comments,
        )
    )

    audit_logger.log(
        AuditAction.PORTAL_ACCESSED,
        AuditResource.CONTRACT_REQUEST,
        resource_id=str(result.contract_request_id),
        details={
            "action": "contract_review",
            "decision": body.decision,
            "third_party_id": str(result.third_party.id),
        },
    )

    decision_msg = (
        "Contrat approuvé."
        if body.decision == "approved"
        else "Demande de modifications envoyée."
    )

    return ContractReviewResponse(
        contract_request_id=result.contract_request_id,
        decision=body.decision,
        message=decision_msg,
    )
