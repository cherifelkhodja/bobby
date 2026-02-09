"""Opportunity schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OpportunityResponse(BaseModel):
    """Opportunity response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    title: str
    reference: str
    budget: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    response_deadline: date | None = None
    manager_name: str | None = None
    manager_boond_id: str | None = None
    client_name: str | None = None
    description: str | None = None
    skills: list[str] = []
    location: str | None = None
    is_open: bool = True
    is_shared: bool = False
    owner_id: str | None = None
    days_until_deadline: int | None = None
    synced_at: datetime
    created_at: datetime


class OpportunityListResponse(BaseModel):
    """Paginated opportunity list response."""

    model_config = ConfigDict(from_attributes=True)

    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
