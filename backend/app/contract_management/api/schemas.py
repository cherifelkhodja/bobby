"""Pydantic schemas for contract management API."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ContractRequestResponse(BaseModel):
    """Contract request response."""

    id: UUID
    reference: str
    boond_positioning_id: int
    status: str
    status_display: str
    third_party_type: str | None = None
    daily_rate: float | None = None
    start_date: date | None = None
    client_name: str | None = None
    mission_description: str | None = None
    commercial_email: str
    third_party_id: UUID | None = None
    compliance_override: bool
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

    third_party_type: str = Field(..., pattern=r"^(freelance|sous_traitant|salarie)$")
    daily_rate: Decimal = Field(..., gt=0)
    start_date: date
    contact_email: EmailStr
    client_name: str | None = Field(None, max_length=255)
    mission_description: str | None = None
    mission_location: str | None = None


class ContractConfigRequest(BaseModel):
    """Request to configure a contract."""

    mission_description: str = ""
    mission_location: str = ""
    start_date: date | None = None
    end_date: date | None = None
    daily_rate: Decimal = Decimal("0")
    estimated_days: int | None = None
    payment_terms: str = "net_30"
    invoice_submission_method: str = "email"
    invoice_email: str = ""
    include_confidentiality: bool = True
    include_non_compete: bool = False
    non_compete_duration_months: int = 0
    non_compete_geographic_scope: str = ""
    include_intellectual_property: bool = True
    include_liability: bool = True
    special_conditions: str = ""


class ComplianceOverrideRequest(BaseModel):
    """Request to override compliance check."""

    reason: str = Field(..., min_length=10, max_length=500)


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
