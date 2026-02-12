"""Published opportunity schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BoondOpportunityResponse(BaseModel):
    """Boond opportunity response for manager's list."""

    model_config = ConfigDict(from_attributes=True)

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
    published_opportunity_id: str | None = None
    published_status: str | None = None
    cooptations_count: int = 0


class BoondOpportunityListResponse(BaseModel):
    """List of Boond opportunities."""

    model_config = ConfigDict(from_attributes=True)

    items: list[BoondOpportunityResponse]
    total: int


class BoondOpportunityDetailResponse(BaseModel):
    """Detailed Boond opportunity response with full information."""

    model_config = ConfigDict(from_attributes=True)

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


class AnonymizeRequest(BaseModel):
    """Request to anonymize an opportunity."""

    boond_opportunity_id: str
    title: str
    description: str | None = None


class AnonymizedPreviewResponse(BaseModel):
    """Preview of anonymized opportunity."""

    model_config = ConfigDict(from_attributes=True)

    boond_opportunity_id: str
    original_title: str
    anonymized_title: str
    anonymized_description: str
    skills: list[str]


class PublishRequest(BaseModel):
    """Request to publish an anonymized opportunity."""

    boond_opportunity_id: str
    title: str
    description: str
    skills: list[str] = []
    original_title: str
    original_data: dict | None = None
    end_date: date | None = None


class PublishedOpportunityResponse(BaseModel):
    """Published opportunity response."""

    model_config = ConfigDict(from_attributes=True)

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


class PublishedOpportunityListResponse(BaseModel):
    """Paginated list of published opportunities."""

    model_config = ConfigDict(from_attributes=True)

    items: list[PublishedOpportunityResponse]
    total: int
    page: int
    page_size: int
