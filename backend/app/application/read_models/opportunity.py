"""Opportunity read models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OpportunityReadModel(BaseModel):
    """Opportunity read model for API responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    external_id: str
    title: str
    reference: str
    budget: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    response_deadline: date | None = None
    manager_name: str | None = None
    client_name: str | None = None
    description: str | None = None
    skills: list[str] = []
    location: str | None = None
    is_open: bool = True
    days_until_deadline: int | None = None
    synced_at: datetime
    created_at: datetime


class OpportunityListReadModel(BaseModel):
    """Paginated opportunity list read model."""

    model_config = ConfigDict(frozen=True)

    items: list[OpportunityReadModel]
    total: int
    page: int
    page_size: int
