"""API schemas for quotation generator."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QuotationPreviewItem(BaseModel):
    """Single quotation in preview."""

    row_index: int
    # Resource info
    resource_name: str
    resource_trigramme: str
    resource_id: str
    # BoondManager relationships
    opportunity_id: str
    company_name: str
    company_id: str
    company_detail_id: str
    contact_name: str
    contact_id: str
    # Period
    period: dict[str, str]
    period_name: str  # Human-readable period name (e.g., "Janvier 2026")
    # Pricing
    tjm: float
    quantity: int
    total_ht: float
    total_ttc: float
    # Thales C22 fields
    c22_domain: str
    c22_activity: str
    complexity: str
    max_price: float  # GFA
    # Other Thales fields
    sow_reference: str
    object_of_need: str
    comments: Optional[str] = None
    start_project: str
    # Additional Thales fields
    eacq_number: str
    is_renewal: bool
    in_situ_ratio: str
    subcontracting: bool
    tier2_supplier: str
    tier3_supplier: str
    # Validation
    is_valid: bool
    validation_errors: list[str]


class PreviewBatchResponse(BaseModel):
    """Response from preview batch endpoint."""

    batch_id: UUID
    total_quotations: int
    valid_count: int
    invalid_count: int
    quotations: list[QuotationPreviewItem]
    validation_errors: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of row index to validation errors",
    )


class StartGenerationRequest(BaseModel):
    """Request to start batch generation."""

    batch_id: UUID
    template_name: str = Field(default="thales_pstf")


class StartGenerationResponse(BaseModel):
    """Response from start generation endpoint."""

    batch_id: UUID
    status: str
    total_quotations: int


class BatchProgressResponse(BaseModel):
    """Response from get progress endpoint."""

    batch_id: str
    status: str
    total: int
    completed: int
    failed: int
    pending: int
    progress_percentage: float
    is_complete: bool
    has_errors: bool
    zip_file_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class QuotationStatusItem(BaseModel):
    """Status of a single quotation in batch details."""

    row_index: int
    resource_name: str
    resource_trigramme: str
    opportunity_id: str
    company_name: str
    status: str
    boond_quotation_id: Optional[str] = None
    boond_reference: Optional[str] = None
    error_message: Optional[str] = None
    is_valid: bool
    validation_errors: list[str]


class BatchDetailsResponse(BaseModel):
    """Detailed response with all quotation statuses."""

    batch_id: str
    user_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total: int
    completed: int
    failed: int
    pending: int
    progress_percentage: float
    is_complete: bool
    has_errors: bool
    zip_file_path: Optional[str] = None
    error_message: Optional[str] = None
    quotations: list[QuotationStatusItem]


class DownloadInfoResponse(BaseModel):
    """Response from download info endpoint."""

    is_ready: bool
    filename: Optional[str] = None
    file_size: Optional[int] = None
    completed_count: int
    failed_count: int


class TemplateInfo(BaseModel):
    """Template information."""

    name: str
    display_name: str
    description: Optional[str] = None
    updated_at: Optional[str] = None


class TemplateListResponse(BaseModel):
    """Response from list templates endpoint."""

    templates: list[TemplateInfo]


class UploadTemplateResponse(BaseModel):
    """Response from upload template endpoint."""

    name: str
    is_valid: bool
    variables_found: list[str]
    missing_variables: list[str]
    warnings: list[str]


class BatchSummary(BaseModel):
    """Summary of a batch for listing."""

    batch_id: str
    status: str
    total: int
    completed: int
    failed: int
    progress_percentage: float
    is_complete: bool
    created_at: Optional[str] = None


class UserBatchesResponse(BaseModel):
    """Response from list user batches endpoint."""

    batches: list[BatchSummary]


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
