"""Cooptation read models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StatusChangeReadModel(BaseModel):
    """Status change history entry."""

    model_config = ConfigDict(frozen=True)

    from_status: str
    to_status: str
    changed_at: datetime
    changed_by: str | None = None
    comment: str | None = None


class CooptationReadModel(BaseModel):
    """Cooptation read model for API responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    candidate_id: str
    candidate_name: str
    candidate_email: str
    candidate_phone: str | None = None
    candidate_daily_rate: float | None = None
    candidate_cv_filename: str | None = None
    candidate_note: str | None = None
    opportunity_id: str
    opportunity_title: str
    opportunity_reference: str
    status: str
    status_display: str
    submitter_id: str
    submitter_name: str | None = None
    external_positioning_id: str | None = None
    rejection_reason: str | None = None
    status_history: list[StatusChangeReadModel] = []
    submitted_at: datetime
    updated_at: datetime


class CooptationListReadModel(BaseModel):
    """Paginated cooptation list read model."""

    model_config = ConfigDict(frozen=True)

    items: list[CooptationReadModel]
    total: int
    page: int
    page_size: int


class CooptationStatsReadModel(BaseModel):
    """Cooptation statistics read model."""

    model_config = ConfigDict(frozen=True)

    total: int
    pending: int
    in_review: int
    interview: int
    accepted: int
    rejected: int
    conversion_rate: float  # accepted / total * 100
