"""Pydantic schemas for third party portal API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ── Portal Responses ──────────────────────────────────────────────


class ThirdPartyPortalResponse(BaseModel):
    """Third party info returned via portal (magic link)."""

    id: UUID
    company_name: str
    contact_email: str
    compliance_status: str
    type: str


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
    company_name: str
    legal_form: str
    capital: str | None = None
    siren: str
    siret: str
    rcs_city: str
    rcs_number: str
    head_office_address: str
    representative_name: str
    representative_title: str
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
    status: str
    file_name: str | None = None
    uploaded_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None


class PortalDocumentsListResponse(BaseModel):
    """List of documents for portal."""

    third_party_id: UUID
    company_name: str
    documents: list[PortalDocumentResponse]


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
