"""Pydantic schemas for vigilance API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Vigilance document response."""

    id: UUID
    third_party_id: UUID
    document_type: str
    document_type_display: str
    status: str
    s3_key: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    uploaded_at: datetime | None = None
    validated_at: datetime | None = None
    validated_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    expires_at: datetime | None = None
    auto_check_results: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ValidateDocumentRequest(BaseModel):
    """Request to validate a document."""

    pass


class RejectDocumentRequest(BaseModel):
    """Request to reject a document."""

    reason: str = Field(..., min_length=5, max_length=1000)


class RequestDocumentsRequest(BaseModel):
    """Request to create document requests for a third party."""

    pass


class ThirdPartyWithDocumentsResponse(BaseModel):
    """Third party with documents summary."""

    id: UUID
    company_name: str
    siren: str
    type: str
    compliance_status: str
    contact_email: str
    documents: list[DocumentResponse]
    document_counts: dict[str, int]


class ComplianceDashboardResponse(BaseModel):
    """Compliance dashboard data."""

    total_third_parties: int
    compliant: int
    non_compliant: int
    expiring_soon: int
    pending: int
    compliance_rate: float
    documents_pending_review: int
    documents_expiring_soon: int
