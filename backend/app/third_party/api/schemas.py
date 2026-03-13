"""Pydantic schemas for third party portal API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ── Portal Responses ──────────────────────────────────────────────


class ThirdPartyPortalResponse(BaseModel):
    """Third party info returned via portal (magic link)."""

    id: UUID
    company_name: str | None = None
    contact_email: str
    compliance_status: str
    type: str
    siren: str | None = None
    # Draft pre-fill fields
    entity_category: str | None = None
    legal_form: str | None = None
    capital: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    ape_code: str | None = None
    rcs_city: str | None = None
    head_office_street: str | None = None
    head_office_postal_code: str | None = None
    head_office_city: str | None = None
    representative_title: str | None = None
    representative_civility: str | None = None
    representative_first_name: str | None = None
    representative_last_name: str | None = None
    representative_email: str | None = None
    representative_phone: str | None = None
    signatory_civility: str | None = None
    signatory_first_name: str | None = None
    signatory_last_name: str | None = None
    signatory_email: str | None = None
    signatory_phone: str | None = None
    signatory_is_director: bool = False
    adv_contact_civility: str | None = None
    adv_contact_first_name: str | None = None
    adv_contact_last_name: str | None = None
    adv_contact_email: str | None = None
    adv_contact_phone: str | None = None
    billing_contact_civility: str | None = None
    billing_contact_first_name: str | None = None
    billing_contact_last_name: str | None = None
    billing_contact_email: str | None = None
    billing_contact_phone: str | None = None
    company_info_submitted: bool = False


class MagicLinkPortalResponse(BaseModel):
    """Portal info returned when verifying a magic link."""

    third_party: ThirdPartyPortalResponse
    purpose: str
    contract_request_id: UUID | None = None


# ── ADV / Admin Schemas ──────────────────────────────────────────


class ThirdPartyResponse(BaseModel):
    """Full third party response for ADV/admin."""

    id: UUID
    boond_provider_id: int | None = None
    type: str
    company_name: str | None = None
    legal_form: str | None = None
    capital: str | None = None
    siren: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    ape_code: str | None = None
    rcs_city: str | None = None
    rcs_number: str | None = None
    head_office_address: str | None = None
    representative_name: str | None = None
    representative_title: str | None = None
    contact_email: str
    compliance_status: str
    created_at: datetime
    updated_at: datetime


class ThirdPartyCreateRequest(BaseModel):
    """Request to create a third party."""

    company_name: str = Field(..., max_length=255)
    legal_form: str = Field(..., max_length=100)
    siren: str = Field(..., min_length=9, max_length=9, pattern=r"^\d{9}$")
    siret: str = Field(..., min_length=14, max_length=14, pattern=r"^\d{14}$")
    rcs_city: str = Field(..., max_length=100)
    rcs_number: str = Field(..., max_length=50)
    head_office_address: str
    representative_name: str = Field(..., max_length=255)
    representative_title: str = Field(..., max_length=255)
    contact_email: EmailStr
    type: str = Field(..., pattern=r"^(freelance|sous_traitant|salarie)$")
    capital: str | None = Field(None, max_length=50)
    boond_provider_id: int | None = None


class ThirdPartyUpdateRequest(BaseModel):
    """Request to update a third party."""

    company_name: str | None = Field(None, max_length=255)
    legal_form: str | None = Field(None, max_length=100)
    capital: str | None = Field(None, max_length=50)
    siret: str | None = Field(None, min_length=14, max_length=14, pattern=r"^\d{14}$")
    rcs_city: str | None = Field(None, max_length=100)
    rcs_number: str | None = Field(None, max_length=50)
    head_office_address: str | None = None
    representative_name: str | None = Field(None, max_length=255)
    representative_title: str | None = Field(None, max_length=255)
    contact_email: EmailStr | None = None
    boond_provider_id: int | None = None


class ThirdPartyListResponse(BaseModel):
    """Paginated list of third parties."""

    items: list[ThirdPartyResponse]
    total: int
    skip: int
    limit: int


class GenerateMagicLinkRequest(BaseModel):
    """Request to generate a magic link."""

    purpose: str = Field(..., pattern=r"^(document_upload|contract_review)$")
    email: EmailStr
    contract_request_id: UUID | None = None


class MagicLinkResponse(BaseModel):
    """Magic link creation response."""

    id: UUID
    token: str
    purpose: str
    email_sent_to: str
    expires_at: datetime
    portal_url: str


# ── Portal Document Upload ──────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document via portal."""

    document_id: UUID
    document_type: str
    status: str
    file_name: str
    message: str = "Document téléversé avec succès."


class PortalDocumentResponse(BaseModel):
    """Document info for portal view."""

    id: UUID
    document_type: str
    display_name: str
    validity_label: str | None = None
    status: str
    file_name: str | None = None
    uploaded_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    # AI-extracted fields
    document_date: date | None = None
    is_valid_at_upload: bool | None = None
    extracted_info: dict | None = None
    # Third-party declared unavailability
    is_unavailable: bool = False
    unavailability_reason: str | None = None


class UpdateDocumentAvailabilityRequest(BaseModel):
    """Request from third party to declare a document unavailable."""

    is_unavailable: bool
    unavailability_reason: str | None = Field(None, max_length=500)


class PortalDocumentsListResponse(BaseModel):
    """List of documents for portal."""

    third_party_id: UUID
    company_name: str | None = None
    documents: list[PortalDocumentResponse]


# ── Portal Document Submission ─────────────────────────────────


class DocumentsSubmittedResponse(BaseModel):
    """Response after the third party confirms their document submission."""

    message: str = "Dépôt validé. Notre équipe va examiner vos documents."


# ── Portal Contract Review ──────────────────────────────────────


class ContractReviewRequest(BaseModel):
    """Request from partner to approve or request changes."""

    decision: str = Field(..., pattern=r"^(approved|changes_requested)$")
    comments: str | None = Field(None, max_length=2000)


class ContractReviewResponse(BaseModel):
    """Response after contract review action."""

    contract_request_id: UUID
    decision: str
    message: str


# ── Portal Company Info ─────────────────────────────────────────


class SiretLookupResponse(BaseModel):
    """Auto-fill data returned from INSEE Sirene + INPI RNE lookup."""

    siren: str | None = None
    company_name: str | None = None
    legal_form: str | None = None
    entity_category: str | None = None
    head_office_street: str | None = None
    head_office_postal_code: str | None = None
    head_office_city: str | None = None
    capital: str | None = None       # From INPI RNE (e.g. "10 000 EUR")
    rcs_city: str | None = None      # From INPI RNE (ville du greffe)
    ape_code: str | None = None      # From INSEE (activité principale)


class CompanyInfoRequest(BaseModel):
    """Request from tiers to submit company identity via portal."""

    entity_category: str = Field(..., pattern=r"^(ei|societe|portage_salarial)$")
    company_name: str = Field(..., max_length=255)
    legal_form: str = Field(..., max_length=100)
    capital: str | None = Field(None, max_length=50)
    siret: str = Field(..., min_length=14, max_length=14, pattern=r"^\d{14}$")
    vat_number: str | None = Field(None, max_length=50, description="Numéro de TVA intracommunautaire")
    ape_code: str | None = Field(None, max_length=10, description="Code APE/NAF")
    head_office_street: str = Field(..., max_length=255)
    head_office_postal_code: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    head_office_city: str = Field(..., max_length=100)
    rcs_city: str | None = Field(None, max_length=100)
    # Représentant légal
    representative_civility: str = Field(..., pattern=r"^(M\.|Mme)$")
    representative_first_name: str = Field(..., max_length=100)
    representative_last_name: str = Field(..., max_length=100)
    representative_email: EmailStr
    representative_phone: str | None = Field(None, max_length=50)
    representative_title: str = Field(..., max_length=255)
    # Signataire du contrat
    signatory_same_as_representative: bool = False
    signatory_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    signatory_first_name: str | None = Field(None, max_length=100)
    signatory_last_name: str | None = Field(None, max_length=100)
    signatory_email: EmailStr | None = None
    signatory_phone: str | None = Field(None, max_length=50)
    signatory_is_director: bool = False
    # Contact ADV
    adv_contact_same_as_representative: bool = False
    adv_contact_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    adv_contact_first_name: str | None = Field(None, max_length=100)
    adv_contact_last_name: str | None = Field(None, max_length=100)
    adv_contact_email: EmailStr | None = None
    adv_contact_phone: str | None = Field(None, max_length=50)
    # Contact facturation
    billing_contact_same_as_representative: bool = False
    billing_contact_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    billing_contact_first_name: str | None = Field(None, max_length=100)
    billing_contact_last_name: str | None = Field(None, max_length=100)
    billing_contact_email: EmailStr | None = None
    billing_contact_phone: str | None = Field(None, max_length=50)


class CompanyInfoDraftRequest(BaseModel):
    """Partial/draft save of company info — all fields optional, no validation constraints."""

    entity_category: str | None = Field(None, pattern=r"^(ei|societe|portage_salarial)$")
    company_name: str | None = Field(None, max_length=255)
    legal_form: str | None = Field(None, max_length=100)
    capital: str | None = Field(None, max_length=50)
    siret: str | None = Field(None, max_length=14)
    vat_number: str | None = Field(None, max_length=50)
    ape_code: str | None = Field(None, max_length=10)
    head_office_street: str | None = Field(None, max_length=255)
    head_office_postal_code: str | None = Field(None, max_length=10)
    head_office_city: str | None = Field(None, max_length=100)
    rcs_city: str | None = Field(None, max_length=100)
    representative_title: str | None = Field(None, max_length=255)
    representative_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    representative_first_name: str | None = Field(None, max_length=100)
    representative_last_name: str | None = Field(None, max_length=100)
    representative_email: EmailStr | None = None
    representative_phone: str | None = Field(None, max_length=50)
    signatory_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    signatory_first_name: str | None = Field(None, max_length=100)
    signatory_last_name: str | None = Field(None, max_length=100)
    signatory_email: EmailStr | None = None
    signatory_phone: str | None = Field(None, max_length=50)
    signatory_is_director: bool | None = None
    adv_contact_same_as_representative: bool | None = None
    adv_contact_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    adv_contact_first_name: str | None = Field(None, max_length=100)
    adv_contact_last_name: str | None = Field(None, max_length=100)
    adv_contact_email: EmailStr | None = None
    adv_contact_phone: str | None = Field(None, max_length=50)
    billing_contact_same_as_representative: bool | None = None
    billing_contact_civility: str | None = Field(None, pattern=r"^(M\.|Mme)$")
    billing_contact_first_name: str | None = Field(None, max_length=100)
    billing_contact_last_name: str | None = Field(None, max_length=100)
    billing_contact_email: EmailStr | None = None
    billing_contact_phone: str | None = Field(None, max_length=50)
