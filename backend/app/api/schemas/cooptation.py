"""Cooptation schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CreateCooptationRequest(BaseModel):
    """Create cooptation request."""

    opportunity_id: str
    candidate_first_name: str = Field(min_length=1, max_length=100)
    candidate_last_name: str = Field(min_length=1, max_length=100)
    candidate_email: EmailStr
    candidate_civility: str = Field(default="M", pattern="^(M|Mme)$")
    candidate_phone: Optional[str] = Field(None, max_length=20)
    candidate_daily_rate: Optional[float] = Field(None, ge=0)
    candidate_note: Optional[str] = Field(None, max_length=2000)


class StatusChangeResponse(BaseModel):
    """Status change history entry."""

    model_config = ConfigDict(from_attributes=True)

    from_status: str
    to_status: str
    changed_at: datetime
    changed_by: Optional[str] = None
    comment: Optional[str] = None


class CooptationResponse(BaseModel):
    """Cooptation response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    candidate_daily_rate: Optional[float] = None
    opportunity_id: str
    opportunity_title: str
    opportunity_reference: str
    status: str
    status_display: str
    submitter_id: str
    submitter_name: Optional[str] = None
    external_positioning_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    status_history: list[StatusChangeResponse] = []
    submitted_at: datetime
    updated_at: datetime


class CooptationListResponse(BaseModel):
    """Paginated cooptation list response."""

    model_config = ConfigDict(from_attributes=True)

    items: list[CooptationResponse]
    total: int
    page: int
    page_size: int


class UpdateCooptationStatusRequest(BaseModel):
    """Update cooptation status request."""

    status: str = Field(
        ...,
        pattern="^(pending|in_review|interview|accepted|rejected)$",
    )
    comment: Optional[str] = Field(None, max_length=500)


class CooptationStatsResponse(BaseModel):
    """Cooptation statistics response."""

    model_config = ConfigDict(from_attributes=True)

    total: int
    pending: int
    in_review: int
    interview: int
    accepted: int
    rejected: int
    conversion_rate: float
