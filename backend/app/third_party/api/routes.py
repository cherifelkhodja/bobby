"""Portal routes for third party magic link access."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.infrastructure.audit.logger import AuditAction, AuditResource, audit_logger
from app.third_party.api.schemas import (
    CompanyInfoRequest,
    ContractReviewRequest,
    ContractReviewResponse,
    DocumentUploadResponse,
    MagicLinkPortalResponse,
    PortalDocumentResponse,
    PortalDocumentsListResponse,
    SiretLookupResponse,
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
            siren=result.third_party.siren,
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

    from app.config import get_settings
    from app.infrastructure.storage.s3_client import S3StorageClient
    from app.vigilance.application.use_cases.upload_document import (
        UploadDocumentCommand,
        UploadDocumentUseCase,
    )

    doc_repo = DocumentRepository(db)
    s3_client = S3StorageClient(get_settings())
    storage = VigilanceDocumentStorage(s3_client)

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

    # Check SIREN uniqueness upfront (another third party may already have it)
    existing = await tp_repo.get_by_siren(siren)
    if existing and existing.id != tp.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le SIREN {siren} est déjà associé à un autre tiers.",
        )

    tp.company_name = body.company_name
    tp.legal_form = body.legal_form
    tp.capital = body.capital
    tp.siren = siren
    tp.siret = body.siret
    tp.rcs_city = body.rcs_city or body.head_office_city
    tp.rcs_number = None
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


# ── INSEE Sirene Lookup ─────────────────────────────────────────


def _map_legal_form(code: str) -> str:
    """Map INSEE categorieJuridiqueUniteLegale code to human-readable form."""
    _MAPPING: dict[str, str] = {
        "1000": "Entrepreneur individuel",
        "1100": "Artisan-commerçant",
        "1200": "Commerçant",
        "1300": "Artisan",
        "2110": "Société en nom collectif",
        "2120": "Société en commandite simple",
        "5110": "SAS unipersonnelle (SASU)",
        "5120": "Société par actions simplifiée (SAS)",
        "5422": "SARL de famille",
        "5498": "EURL",
        "5499": "Société à responsabilité limitée (SARL)",
        "5599": "SA à conseil d'administration",
        "5710": "Société anonyme (SA)",
        "5720": "SA à directoire",
        "5800": "Société en commandite par actions",
        "6540": "Association loi 1901",
        "9220": "Association déclarée",
    }
    return _MAPPING.get(code, code)


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

    return SiretLookupResponse(
        siren=siren,
        company_name=company_name,
        legal_form=legal_form,
        entity_category=entity_category if categorie_code else None,
        head_office_street=street,
        head_office_postal_code=postal_code,
        head_office_city=city,
    )
