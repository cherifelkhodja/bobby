"""Portal routes for third party magic link access."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.third_party.api.schemas import (
    CompanyInfoDraftRequest,
    CompanyInfoRequest,
    ContractReviewRequest,
    ContractReviewResponse,
    DocumentUploadResponse,
    DocumentsSubmittedResponse,
    MagicLinkPortalResponse,
    PortalDocumentResponse,
    PortalDocumentsListResponse,
    SiretLookupResponse,
    ThirdPartyPortalResponse,
    UpdateDocumentAvailabilityRequest,
)
from app.third_party.application.use_cases.verify_magic_link import (
    VerifyMagicLinkUseCase,
)
from app.third_party.domain.exceptions import (
    MagicLinkExpiredError,
    MagicLinkNotFoundError,
    MagicLinkRevokedError,
)
from app.vigilance.domain.exceptions import (
    DocumentNotAllowedError,
    DocumentNotFoundError,
    ExpiredDocumentError,
    InvalidDocumentTransitionError,
)
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
from app.third_party.infrastructure.adapters.postgres_magic_link_repo import (
    MagicLinkRepository,
)
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)
from app.vigilance.infrastructure.adapters.gemini_document_extractor import (
    GeminiDocumentExtractor,
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

    tp = result.third_party
    return MagicLinkPortalResponse(
        third_party=ThirdPartyPortalResponse(
            id=tp.id,
            company_name=tp.company_name,
            contact_email=tp.contact_email,
            compliance_status=tp.compliance_status.value,
            type=tp.type.value,
            siren=tp.siren,
            entity_category=tp.entity_category,
            legal_form=tp.legal_form,
            capital=tp.capital,
            siret=tp.siret,
            rcs_city=tp.rcs_city,
            head_office_street=tp.head_office_street,
            head_office_postal_code=tp.head_office_postal_code,
            head_office_city=tp.head_office_city,
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
            company_info_submitted=tp.company_info_submitted,
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
                display_name=doc.document_type.display_name,
                validity_label=doc.document_type.validity_label,
                status=doc.status.value,
                file_name=doc.file_name,
                uploaded_at=doc.uploaded_at,
                rejected_at=doc.rejected_at,
                rejection_reason=doc.rejection_reason,
                document_date=doc.document_date,
                is_valid_at_upload=doc.is_valid_at_upload,
                extracted_info=doc.auto_check_results,
                is_unavailable=doc.is_unavailable,
                unavailability_reason=doc.unavailability_reason,
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

    from app.config import get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient
    from app.vigilance.application.use_cases.upload_document import (
        UploadDocumentCommand,
        UploadDocumentUseCase,
    )

    doc_repo = DocumentRepository(db)
    s3_client = S3StorageClient(get_settings())
    storage = VigilanceDocumentStorage(s3_client)
    extractor = GeminiDocumentExtractor(get_settings())

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


# ── Portal Document Availability ────────────────────────────────


@router.patch(
    "/portal/{token}/documents/{document_id}/availability",
    response_model=PortalDocumentResponse,
    summary="Declare a document unavailable (or reset)",
)
async def update_document_availability(
    token: str,
    document_id: UUID,
    body: UpdateDocumentAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    """Third party declares they cannot provide a document, or resets that declaration."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.third_party_id != result.third_party.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    if body.is_unavailable:
        if not body.unavailability_reason or not body.unavailability_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Une raison est requise pour signaler un document indisponible.",
            )
        doc.mark_unavailable(body.unavailability_reason)
    else:
        doc.mark_available()

    saved = await doc_repo.save(doc)

    return PortalDocumentResponse(
        id=saved.id,
        document_type=saved.document_type.value,
        display_name=saved.document_type.display_name,
        validity_label=saved.document_type.validity_label,
        status=saved.status.value,
        file_name=saved.file_name,
        uploaded_at=saved.uploaded_at,
        rejected_at=saved.rejected_at,
        rejection_reason=saved.rejection_reason,
        document_date=saved.document_date,
        is_valid_at_upload=saved.is_valid_at_upload,
        extracted_info=saved.auto_check_results,
        is_unavailable=saved.is_unavailable,
        unavailability_reason=saved.unavailability_reason,
    )


# ── Portal Document Delete (reset to requested) ─────────────────


@router.delete(
    "/portal/{token}/documents/{document_id}",
    summary="Delete a transmitted document (reset to requested)",
    status_code=status.HTTP_200_OK,
)
async def delete_portal_document(
    token: str,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Third party resets a received document back to 'requested', deleting the uploaded file."""
    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    from app.config import get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient

    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.third_party_id != result.third_party.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    if doc.status.value not in ("received",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Seuls les documents transmis peuvent être supprimés.",
        )

    old_s3_key = doc.s3_key
    doc.re_request()
    await doc_repo.save(doc)

    # Best-effort S3 deletion
    if old_s3_key:
        try:
            s3_client = S3StorageClient(get_settings())
            storage = VigilanceDocumentStorage(s3_client)
            await storage.delete(old_s3_key)
        except Exception:
            logger.warning("portal_document_s3_delete_failed", s3_key=old_s3_key)

    audit_logger.log(
        AuditAction.DOCUMENT_UPLOADED,
        AuditResource.VIGILANCE_DOCUMENT,
        resource_id=str(doc.id),
        details={
            "third_party_id": str(result.third_party.id),
            "document_type": doc.document_type.value,
            "action": "deleted_by_portal",
        },
    )

    return {"message": "Document supprimé. Vous pouvez en déposer un nouveau."}


# ── Portal Submit Documents ─────────────────────────────────────


@router.post(
    "/portal/{token}/submit-documents",
    response_model=DocumentsSubmittedResponse,
    summary="Third party confirms document submission",
)
async def submit_portal_documents(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Called when the third party clicks 'Valider le dépôt'.

    - Sets compliance_status to UNDER_REVIEW on the third party.
    - Sends notification email to the ADV contact and all admin users.
    Never blocks on email failure.
    """
    from app.config import get_settings
    from app.infrastructure.database.repositories.user_repository import UserRepository
    from app.infrastructure.email.sender import EmailService as EmailSender
    from app.domain.value_objects import UserRole
    from app.third_party.infrastructure.models import ThirdPartyModel

    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    doc_repo = DocumentRepository(db)
    documents = await doc_repo.list_by_third_party(result.third_party.id)

    uploaded_count = sum(
        1 for d in documents
        if d.status.value in ("received", "validated", "expiring_soon")
    )
    total_count = len(documents)

    # Update compliance status to "En cours de vérification" (best-effort)
    try:
        tp_model = await db.get(ThirdPartyModel, result.third_party.id)
        if tp_model:
            tp_model.compliance_status = "under_review"
            await db.flush()
    except Exception as exc:
        logger.warning(
            "compliance_status_update_failed",
            third_party_id=str(result.third_party.id),
            error=str(exc),
        )

    # Transition contract request from COLLECTING_DOCUMENTS → REVIEWING_COMPLIANCE (best-effort)
    if result.contract_request_id:
        try:
            from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
                ContractRequestRepository,
            )
            from app.contract_management.domain.value_objects.contract_request_status import (
                ContractRequestStatus,
            )

            cr_repo = ContractRequestRepository(db)
            cr = await cr_repo.get_by_id(result.contract_request_id)
            if cr and cr.status == ContractRequestStatus.COLLECTING_DOCUMENTS:
                cr.transition_to(ContractRequestStatus.REVIEWING_COMPLIANCE)
                await cr_repo.save(cr)
        except Exception as exc:
            logger.warning(
                "contract_request_status_update_failed",
                contract_request_id=str(result.contract_request_id),
                error=str(exc),
            )

    # Collect recipients: ADV and admin users in Bobby
    settings = get_settings()
    email_sender = EmailSender(settings)
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    compliance_url = f"{frontend_url}/compliance"
    third_party_name = result.third_party.company_name or result.third_party.contact_email

    user_repo = UserRepository(db)
    internal_users = await user_repo.list_by_roles([UserRole.ADV, UserRole.ADMIN])
    recipients: list[str] = []
    for u in internal_users:
        email = str(u.email)
        if email and email not in recipients:
            recipients.append(email)

    for recipient in recipients:
        try:
            await email_sender.send_documents_submitted_notification(
                to=recipient,
                third_party_name=third_party_name,
                uploaded_count=uploaded_count,
                total_count=total_count,
                compliance_url=compliance_url,
            )
        except Exception as exc:
            logger.warning(
                "submit_notification_email_failed",
                third_party_id=str(result.third_party.id),
                recipient=recipient,
                error=str(exc),
            )

    audit_logger.log(
        AuditAction.PORTAL_ACCESSED,
        AuditResource.MAGIC_LINK,
        resource_id=str(result.magic_link.id),
        details={
            "action": "documents_submitted",
            "third_party_id": str(result.third_party.id),
            "uploaded_count": uploaded_count,
            "total_count": total_count,
        },
    )

    return DocumentsSubmittedResponse()


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

    # Generate presigned S3 URL so the portal can display the PDF inline
    download_url = None
    if contract.s3_key_draft:
        from app.infrastructure.storage.s3_client import S3StorageClient
        from app.config import get_settings
        s3 = S3StorageClient(get_settings())
        download_url = await s3.get_presigned_url(contract.s3_key_draft, expires_in=1800)

    return {
        "contract_request_id": str(result.contract_request_id),
        "status": contract.yousign_status or "draft",
        "download_url": download_url,
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

    from app.config import get_settings
    from app.contract_management.application.use_cases.process_partner_review import (
        ProcessPartnerReviewUseCase,
    )
    from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
        ContractRepository,
        ContractRequestRepository,
    )
    from app.infrastructure.email.sender import EmailService

    settings = get_settings()
    cr_repo = ContractRequestRepository(db)
    contract_repo = ContractRepository(db)
    email_service = EmailService(settings)
    use_case = ProcessPartnerReviewUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        email_service=email_service,
    )

    updated = await use_case.execute(
        contract_request_id=result.contract_request_id,
        approved=body.decision == "approved",
        comments=body.comments,
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
        "Contrat approuvé." if body.decision == "approved" else "Demande de modifications envoyée."
    )

    return ContractReviewResponse(
        contract_request_id=result.contract_request_id,
        decision=body.decision,
        message=decision_msg,
    )


# ── Portal Company Info ─────────────────────────────────────────


@router.post(
    "/portal/{token}/company-info",
    summary="Submit company identity info via portal",
)
async def submit_company_info(
    token: str,
    body: CompanyInfoRequest,
    db: AsyncSession = Depends(get_db),
):
    """Tiers fills in their company identity (SIREN, raison sociale, etc.).
    Called when the ThirdParty stub was created without this data.
    Once saved, the portal unlocks the document upload section.
    """
    from sqlalchemy.exc import IntegrityError

    from app.vigilance.application.use_cases.request_documents import RequestDocumentsUseCase
    from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository

    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)
    tp = result.third_party
    tp_repo = ThirdPartyRepository(db)

    # Derive SIREN from first 9 digits of SIRET
    siren = body.siret[:9]

    tp.entity_category = body.entity_category
    tp.company_info_submitted = True
    tp.company_name = body.company_name
    tp.legal_form = body.legal_form
    tp.capital = body.capital
    tp.siren = siren
    tp.siret = body.siret
    tp.rcs_city = body.rcs_city or body.head_office_city
    tp.rcs_number = None
    tp.head_office_street = body.head_office_street
    tp.head_office_postal_code = body.head_office_postal_code
    tp.head_office_city = body.head_office_city
    tp.head_office_address = (
        f"{body.head_office_street}, {body.head_office_postal_code} {body.head_office_city}"
    )
    # Représentant légal
    tp.representative_civility = body.representative_civility
    tp.representative_first_name = body.representative_first_name
    tp.representative_last_name = body.representative_last_name
    tp.representative_email = body.representative_email
    tp.representative_phone = body.representative_phone
    tp.representative_title = body.representative_title
    tp.representative_name = f"{body.representative_first_name} {body.representative_last_name}"
    # Signataire
    if body.signatory_same_as_representative:
        tp.signatory_civility = body.representative_civility
        tp.signatory_first_name = body.representative_first_name
        tp.signatory_last_name = body.representative_last_name
        tp.signatory_email = body.representative_email
        tp.signatory_phone = body.representative_phone
    else:
        tp.signatory_civility = body.signatory_civility
        tp.signatory_first_name = body.signatory_first_name
        tp.signatory_last_name = body.signatory_last_name
        tp.signatory_email = body.signatory_email
        tp.signatory_phone = body.signatory_phone
    # Contact ADV
    if body.adv_contact_same_as_representative:
        tp.adv_contact_civility = body.representative_civility
        tp.adv_contact_first_name = body.representative_first_name
        tp.adv_contact_last_name = body.representative_last_name
        tp.adv_contact_email = body.representative_email
        tp.adv_contact_phone = body.representative_phone
    else:
        tp.adv_contact_civility = body.adv_contact_civility
        tp.adv_contact_first_name = body.adv_contact_first_name
        tp.adv_contact_last_name = body.adv_contact_last_name
        tp.adv_contact_email = body.adv_contact_email
        tp.adv_contact_phone = body.adv_contact_phone
    # Contact facturation
    if body.billing_contact_same_as_representative:
        tp.billing_contact_civility = body.representative_civility
        tp.billing_contact_first_name = body.representative_first_name
        tp.billing_contact_last_name = body.representative_last_name
        tp.billing_contact_email = body.representative_email
        tp.billing_contact_phone = body.representative_phone
    else:
        tp.billing_contact_civility = body.billing_contact_civility
        tp.billing_contact_first_name = body.billing_contact_first_name
        tp.billing_contact_last_name = body.billing_contact_last_name
        tp.billing_contact_email = body.billing_contact_email
        tp.billing_contact_phone = body.billing_contact_phone

    try:
        await tp_repo.save(tp)
    except IntegrityError as exc:
        logger.error("company_info_save_failed", error=str(exc), third_party_id=str(tp.id))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une contrainte d'intégrité a empêché l'enregistrement. Vérifiez le SIREN.",
        )

    # Create vigilance document stubs now that we know the entity category
    doc_repo = DocumentRepository(db)
    request_docs_uc = RequestDocumentsUseCase(
        third_party_repository=tp_repo,
        document_repository=doc_repo,
    )
    await request_docs_uc.execute(tp.id, entity_category=body.entity_category)

    audit_logger.log(
        AuditAction.PORTAL_ACCESSED,
        AuditResource.MAGIC_LINK,
        resource_id=str(result.magic_link.id),
        details={
            "action": "company_info_submitted",
            "third_party_id": str(tp.id),
            "siret": body.siret,
            "siren": siren,
            "entity_category": body.entity_category,
        },
    )

    return {"message": "Informations enregistrées avec succès."}


@router.patch(
    "/portal/{token}/company-info",
    summary="Save partial/draft company info via portal",
)
async def save_company_info_draft(
    token: str,
    body: CompanyInfoDraftRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save a partial draft of company info without completing the form.

    Unlike POST (which validates all required fields and creates document stubs),
    PATCH accepts any subset of fields and simply persists them so the tiers can
    resume filling the form later.
    Uses a targeted SQL UPDATE to avoid loading/saving the full ORM entity.
    """
    result = await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)
    third_party_id = result.third_party.id

    # Build only the columns that were explicitly provided
    updates: dict[str, object] = {}

    field_map = {
        "entity_category": body.entity_category,
        "company_name": body.company_name,
        "legal_form": body.legal_form,
        "capital": body.capital,
        "siret": body.siret,
        "head_office_street": body.head_office_street,
        "head_office_postal_code": body.head_office_postal_code,
        "head_office_city": body.head_office_city,
        "rcs_city": body.rcs_city,
        "representative_title": body.representative_title,
        "representative_civility": body.representative_civility,
        "representative_first_name": body.representative_first_name,
        "representative_last_name": body.representative_last_name,
        "representative_email": str(body.representative_email) if body.representative_email else None,
        "representative_phone": body.representative_phone,
        "signatory_civility": body.signatory_civility,
        "signatory_first_name": body.signatory_first_name,
        "signatory_last_name": body.signatory_last_name,
        "signatory_email": str(body.signatory_email) if body.signatory_email else None,
        "signatory_phone": body.signatory_phone,
        "adv_contact_civility": body.adv_contact_civility,
        "adv_contact_first_name": body.adv_contact_first_name,
        "adv_contact_last_name": body.adv_contact_last_name,
        "adv_contact_email": str(body.adv_contact_email) if body.adv_contact_email else None,
        "adv_contact_phone": body.adv_contact_phone,
        "billing_contact_civility": body.billing_contact_civility,
        "billing_contact_first_name": body.billing_contact_first_name,
        "billing_contact_last_name": body.billing_contact_last_name,
        "billing_contact_email": str(body.billing_contact_email) if body.billing_contact_email else None,
        "billing_contact_phone": body.billing_contact_phone,
    }

    for col, val in field_map.items():
        if val is not None:
            updates[col] = val

    # Also derive siren from siret when provided
    if body.siret and len(body.siret) >= 9:
        updates["siren"] = body.siret[:9]

    if not updates:
        return {"message": "Rien à enregistrer."}

    from app.third_party.infrastructure.models import ThirdPartyModel

    await db.execute(
        update(ThirdPartyModel)
        .where(ThirdPartyModel.id == third_party_id)
        .values(**updates)
    )

    logger.info("company_info_draft_saved", third_party_id=str(third_party_id), fields=list(updates.keys()))
    return {"message": "Brouillon enregistré."}


# ── INSEE Sirene Lookup ─────────────────────────────────────────


def _map_legal_form(code: str) -> str | None:
    """Map INSEE categorieJuridiqueUniteLegale code to human-readable form.

    Delegates to the canonical FORME_JURIDIQUE_LABELS dict (same source as the
    frontend dropdown) so the returned label always matches a select option.
    """
    from app.third_party.infrastructure.adapters.inpi_client import forme_juridique_label

    return forme_juridique_label(code)


@router.get(
    "/portal/{token}/siret/{siret}",
    response_model=SiretLookupResponse,
    summary="Lookup SIRET via INSEE Sirene API (portal proxy)",
)
async def lookup_siret(
    token: str,
    siret: str,
    db: AsyncSession = Depends(get_db),
):
    """Look up company information from INSEE Sirene API for auto-fill.

    The magic link token authenticates the request.
    The INSEE API key is read from server-side configuration.
    """
    import httpx

    from app.config import get_settings

    # Verify the portal token (any valid doc_upload link)
    await _verify_portal_token(token, db, MagicLinkPurpose.DOCUMENT_UPLOAD)

    settings = get_settings()
    if not settings.SIRENE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INSEE Sirene API non configurée.",
        )

    if len(siret) != 14 or not siret.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIRET invalide (14 chiffres requis).",
        )

    url = f"{settings.SIRENE_API_URL}/siret/{siret}"
    headers = {
        "X-INSEE-Api-Key-Integration": settings.SIRENE_API_KEY,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="L'API INSEE n'a pas répondu à temps.",
        )
    except Exception as exc:
        logger.error("sirene_lookup_error", error=str(exc), siret=siret)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors de la communication avec l'API INSEE.",
        )

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIRET introuvable dans la base INSEE.",
        )
    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Clé API INSEE invalide.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur INSEE ({resp.status_code}).",
        )

    data = resp.json()
    etab = data.get("etablissement", {})
    unite = etab.get("uniteLegale", {})
    adresse = etab.get("adresseEtablissement", {})

    def _clean(val: str | None) -> str | None:
        """Return None if value is [ND] or empty."""
        if not val or val == "[ND]":
            return None
        return val

    siren = _clean(etab.get("siren"))
    company_name = _clean(unite.get("denominationUniteLegale"))
    categorie_code = _clean(unite.get("categorieJuridiqueUniteLegale")) or ""
    legal_form = _map_legal_form(categorie_code) if categorie_code else None
    entity_category = "ei" if categorie_code.startswith("1") else "societe"

    # Build address
    parts = [
        _clean(adresse.get("numeroVoieEtablissement")),
        _clean(adresse.get("indiceRepetitionEtablissement")),
        _clean(adresse.get("typeVoieEtablissement")),
        _clean(adresse.get("libelleVoieEtablissement")),
    ]
    street = " ".join(p for p in parts if p) or None
    postal_code = _clean(adresse.get("codePostalEtablissement"))
    city = _clean(adresse.get("libelleCommuneEtablissement"))

    # Enrich with INPI RNE data (forme juridique, capital, greffe) — uses SIREN (first 9 digits)
    capital_str: str | None = None
    rcs_city: str | None = None
    inpi_configured = bool(settings.INPI_USERNAME and settings.INPI_PASSWORD) or bool(settings.INPI_TOKEN)
    if siren and inpi_configured:
        from app.third_party.infrastructure.adapters.inpi_client import InpiClient
        try:
            inpi = InpiClient(
                username=settings.INPI_USERNAME,
                password=settings.INPI_PASSWORD,
                token=settings.INPI_TOKEN,
            )
            inpi_info = await inpi.get_company(siren)
            if not inpi_info:
                logger.warning("inpi_no_data_returned", siren=siren)
            if inpi_info:
                # Forme juridique : INPI est source de vérité (RNE officiel)
                if inpi_info.legal_form_label:
                    legal_form = inpi_info.legal_form_label
                if inpi_info.capital_amount is not None:
                    capital_str = f"{inpi_info.capital_amount:,.0f}".replace(",", " ")
                rcs_city = inpi_info.greffe_city
        except Exception as exc:
            logger.warning("inpi_enrich_failed", siren=siren, error=str(exc), error_type=type(exc).__name__)

    return SiretLookupResponse(
        siren=siren,
        company_name=company_name,
        legal_form=legal_form,
        entity_category=entity_category if categorie_code else None,
        head_office_street=street,
        head_office_postal_code=postal_code,
        head_office_city=city,
        capital=capital_str,
        rcs_city=rcs_city,
    )
