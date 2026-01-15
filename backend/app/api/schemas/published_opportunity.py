"""Published opportunity schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BoondOpportunityResponse(BaseModel):
    """Boond opportunity response for manager's list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    reference: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    company_name: Optional[str] = None
    state: Optional[int] = None
    state_name: Optional[str] = None
    is_published: bool = False


class BoondOpportunityListResponse(BaseModel):
    """List of Boond opportunities."""

    model_config = ConfigDict(from_attributes=True)

    items: list[BoondOpportunityResponse]
    total: int


class AnonymizeRequest(BaseModel):
    """Request to anonymize an opportunity."""

    boond_opportunity_id: str
    title: str
    description: Optional[str] = None


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
    original_data: Optional[dict] = None
    end_date: Optional[date] = None


class PublishedOpportunityResponse(BaseModel):
    """Published opportunity response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    boond_opportunity_id: str
    title: str
    description: str
    skills: list[str] = []
    end_date: Optional[date] = None
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
