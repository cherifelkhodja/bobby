"""Published opportunity read models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BoondOpportunityReadModel(BaseModel):
    """Boond opportunity read model for manager's opportunity list."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    reference: str
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    company_name: str | None = None
    state: int | None = None
    state_name: str | None = None
    state_color: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    is_published: bool = False


class BoondOpportunityDetailReadModel(BaseModel):
    """Detailed Boond opportunity read model with full information."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    reference: str
    description: str | None = None
    criteria: str | None = None
    expertise_area: str | None = None
    place: str | None = None
    duration: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    closing_date: str | None = None
    answer_date: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    contact_id: str | None = None
    contact_name: str | None = None
    agency_id: str | None = None
    agency_name: str | None = None
    state: int | None = None
    state_name: str | None = None
    state_color: str | None = None
    is_published: bool = False


class BoondOpportunityListReadModel(BaseModel):
    """List of Boond opportunities for manager."""

    model_config = ConfigDict(frozen=True)

    items: list[BoondOpportunityReadModel]
    total: int


class AnonymizedPreviewReadModel(BaseModel):
    """Preview of anonymized opportunity before publishing."""

    model_config = ConfigDict(frozen=True)

    boond_opportunity_id: str
    original_title: str
    anonymized_title: str
    anonymized_description: str
    skills: list[str]


class PublishedOpportunityReadModel(BaseModel):
    """Published opportunity read model for API responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    boond_opportunity_id: str
    title: str
    description: str
    skills: list[str] = []
    end_date: date | None = None
    status: str
    status_display: str
    created_at: datetime
    updated_at: datetime


class PublishedOpportunityListReadModel(BaseModel):
    """Paginated published opportunity list read model."""

    model_config = ConfigDict(frozen=True)

    items: list[PublishedOpportunityReadModel]
    total: int
    page: int
    page_size: int
