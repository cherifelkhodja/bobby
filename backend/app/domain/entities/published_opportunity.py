"""Published opportunity domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.value_objects.status import OpportunityStatus


@dataclass
class PublishedOpportunity:
    """Published opportunity entity representing an anonymized opportunity for cooptation."""

    boond_opportunity_id: str
    title: str
    description: str
    published_by: UUID
    skills: list[str] = field(default_factory=list)
    original_title: str | None = None
    original_data: dict[str, Any] | None = None
    end_date: date | None = None
    status: OpportunityStatus = OpportunityStatus.PUBLISHED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_visible(self) -> bool:
        """Check if opportunity is visible to consultants."""
        return self.status.is_visible_to_consultants

    @property
    def is_expired(self) -> bool:
        """Check if opportunity has passed its end date."""
        if not self.end_date:
            return False
        return date.today() > self.end_date

    def close(self) -> None:
        """Close the opportunity."""
        self.status = OpportunityStatus.CLOSED
        self.updated_at = datetime.utcnow()

    def publish(self) -> None:
        """Publish the opportunity (from draft)."""
        self.status = OpportunityStatus.PUBLISHED
        self.updated_at = datetime.utcnow()

    def update_content(self, title: str, description: str, skills: list[str]) -> None:
        """Update the anonymized content."""
        self.title = title
        self.description = description
        self.skills = skills
        self.updated_at = datetime.utcnow()
