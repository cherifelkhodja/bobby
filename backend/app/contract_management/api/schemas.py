"""Pydantic schemas for contract management API."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ContractRequestResponse(BaseModel):
    """Contract request response."""

    id: UUID
    provisional_reference: str
    reference: str | None = None
    display_reference: str
    boond_positioning_id: int
    boond_candidate_id: int | None = None
    boond_consultant_type: str | None = None
    status: str
    status_display: str
    third_party_type: str | None = None
    daily_rate: float | None = None
    quantity_sold: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    client_name: str | None = None
    mission_title: str | None = None
    mission_description: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None
    mission_site_name: str | None = None
    mission_address: str | None = None
    mission_postal_code: str | None = None
    mission_city: str | None = None
    commercial_email: str
    commercial_name: str | None = None
    contractualization_contact_email: str | None = None
    third_party_id: UUID | None = None
    portal_url: str | None = None
    compliance_override: bool
    contract_config: dict | None = None
    status_history: list[dict] = []
    created_at: datetime
    updated_at: datetime


class ContractRequestListResponse(BaseModel):
    """Paginated list of contract requests."""

    items: list[ContractRequestResponse]
    total: int
    skip: int
    limit: int


class CommercialValidationRequest(BaseModel):
    """Request for commercial validation."""

    third_party_type: str = Field(..., pattern=r"^(freelance|sous_traitant|salarie|portage_salarial)$")
    daily_rate: Decimal = Field(..., gt=0)
    start_date: date
    end_date: date | None = None
    contact_email: EmailStr
    client_name: str | None = Field(None, max_length=255)
    mission_title: str | None = Field(None, max_length=500)
    mission_description: str | None = None
    consultant_civility: str | None = Field(None, max_length=10)
    consultant_first_name: str | None = Field(None, max_length=255)
    consultant_last_name: str | None = Field(None, max_length=255)
    consultant_email: str | None = Field(None, max_length=255)
    consultant_phone: str | None = Field(None, max_length=50)
    mission_site_name: str | None = Field(None, max_length=255)
    mission_address: str | None = Field(None, max_length=500)
    mission_postal_code: str | None = Field(None, max_length=10)
    mission_city: str | None = Field(None, max_length=255)


class ContractConfigRequest(BaseModel):
    """Request to configure a contract.

    payment_terms values: "immediate" (comptant), "net_30" (30 jours), "net_45_eom" (45 jours fin de mois)
    invoice_submission_method values: "email" (factures@geminiconsulting.fr), "boondmanager"
    """

    company_id: UUID | None = None
    mission_description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    daily_rate: Decimal = Decimal("0")
    estimated_days: int | None = None
    payment_terms: str = "net_30"
    invoice_submission_method: str = "email"
    invoice_email: str = ""
    tacit_renewal_months: int | None = Field(None, ge=1, le=24, description="Nombre de mois pour la tacite reconduction (annexe)")
    excluded_optional_article_keys: list[str] = Field(default_factory=list, description="Clés des articles optionnels à exclure du contrat")
    special_conditions: str = ""


# ── Contract companies ────────────────────────────────────────────────────────

class ContractCompanyRequest(BaseModel):
    """Create or update an issuing company."""

    name: str = Field(..., max_length=255)
    code: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z0-9]{3}$", description="3-letter code used in contract references (e.g. GEM, GCI)")
    legal_form: str = Field(..., max_length=50)
    capital: str = Field(..., max_length=100)
    head_office: str = Field(..., max_length=500)
    rcs_city: str = Field(..., max_length=100)
    rcs_number: str = Field(..., max_length=50)
    representative_is_entity: bool = False
    representative_name: str = Field(..., max_length=255)
    representative_quality: str = Field(..., max_length=255)
    representative_sub_name: str | None = Field(None, max_length=255)
    representative_sub_quality: str | None = Field(None, max_length=255)
    signatory_name: str = Field(..., max_length=255)
    invoices_company_mail: str | None = Field(None, max_length=255)
    color_code: str = Field("#4BBEA8", pattern=r"^#[0-9A-Fa-f]{6}$")
    boond_agency_id: int | None = Field(None, description="ID de l'agence Boond associée à cette société émettrice")
    is_default: bool = False
    is_active: bool = True


class ContractCompanyResponse(BaseModel):
    """Issuing company response."""

    id: UUID
    name: str
    code: str
    legal_form: str
    capital: str
    head_office: str
    rcs_city: str
    rcs_number: str
    representative_is_entity: bool
    representative_name: str
    representative_quality: str
    representative_sub_name: str | None = None
    representative_sub_quality: str | None = None
    signatory_name: str
    invoices_company_mail: str | None = None
    color_code: str
    boond_agency_id: int | None = None
    has_logo: bool
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ComplianceOverrideRequest(BaseModel):
    """Request to override compliance check."""

    reason: str = Field(..., min_length=10, max_length=500)


class ArticleOverridesRequest(BaseModel):
    """Per-contract article/annex content overrides.

    Keys are article_key / annexe_key; values are the overridden HTML content.
    Pass an empty string to reset an override (restores template default).
    deleted_article_keys / deleted_annex_keys: keys to exclude from the PDF.
    Pass an empty list to clear all deletions for that type.
    """

    article_overrides: dict[str, str] = Field(default_factory=dict)
    annex_overrides: dict[str, str] = Field(default_factory=dict)
    deleted_article_keys: list[str] | None = None
    deleted_annex_keys: list[str] | None = None


class PartnerReviewRequest(BaseModel):
    """Request from partner reviewing a contract draft."""

    approved: bool
    comments: str | None = Field(None, max_length=2000)


class ContractResponse(BaseModel):
    """Contract document response."""

    id: UUID
    contract_request_id: UUID
    reference: str
    version: int
    s3_key_draft: str
    s3_key_signed: str | None = None
    yousign_status: str | None = None
    partner_comments: str | None = None
    created_at: datetime
    signed_at: datetime | None = None


class WebhookResponse(BaseModel):
    """Standard webhook response (always 200 OK)."""

    status: str = "ok"
    message: str = ""
