"""Published opportunity read models."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BoondOpportunityReadModel(BaseModel):
    """Boond opportunity read model for manager's opportunity list."""

    model_config = ConfigDict(frozen=True)

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
    end_date: Optional[date] = None
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
