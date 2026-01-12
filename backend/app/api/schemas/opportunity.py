"""Opportunity schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpportunityResponse(BaseModel):
    """Opportunity response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    title: str
    reference: str
    budget: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    response_deadline: Optional[date] = None
    manager_name: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = []
    location: Optional[str] = None
    is_open: bool = True
    days_until_deadline: Optional[int] = None
    synced_at: datetime
    created_at: datetime


class OpportunityListResponse(BaseModel):
    """Paginated opportunity list response."""

    model_config = ConfigDict(from_attributes=True)

    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
