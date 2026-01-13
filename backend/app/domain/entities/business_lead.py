"""Business Lead domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class BusinessLeadStatus(str, Enum):
    """Business lead status lifecycle."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    QUALIFIED = "qualified"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable status name."""
        names = {
            BusinessLeadStatus.DRAFT: "Brouillon",
            BusinessLeadStatus.SUBMITTED: "Soumis",
            BusinessLeadStatus.IN_REVIEW: "En cours d'examen",
            BusinessLeadStatus.QUALIFIED: "Qualifié",
            BusinessLeadStatus.REJECTED: "Rejeté",
        }
        return names[self]

    @property
    def is_final(self) -> bool:
        """Check if status is final."""
        return self in (BusinessLeadStatus.QUALIFIED, BusinessLeadStatus.REJECTED)


@dataclass
class BusinessLead:
    """Business Lead entity representing an opportunity brought by a user."""

    title: str
    description: str
    submitter_id: UUID  # User who submitted the lead
    client_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    estimated_budget: Optional[float] = None
    expected_start_date: Optional[date] = None
    skills_needed: list[str] = field(default_factory=list)
    location: Optional[str] = None
    status: BusinessLeadStatus = BusinessLeadStatus.DRAFT
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def submit(self) -> None:
        """Submit the business lead for review."""
        if self.status != BusinessLeadStatus.DRAFT:
            raise ValueError("Can only submit draft leads")
        self.status = BusinessLeadStatus.SUBMITTED
        self.updated_at = datetime.utcnow()

    def start_review(self) -> None:
        """Mark lead as being reviewed."""
        if self.status != BusinessLeadStatus.SUBMITTED:
            raise ValueError("Can only review submitted leads")
        self.status = BusinessLeadStatus.IN_REVIEW
        self.updated_at = datetime.utcnow()

    def qualify(self) -> None:
        """Qualify the business lead."""
        if self.status not in (BusinessLeadStatus.SUBMITTED, BusinessLeadStatus.IN_REVIEW):
            raise ValueError("Can only qualify submitted or in-review leads")
        self.status = BusinessLeadStatus.QUALIFIED
        self.updated_at = datetime.utcnow()

    def reject(self, reason: Optional[str] = None) -> None:
        """Reject the business lead."""
        if self.status.is_final:
            raise ValueError("Cannot reject a lead with final status")
        self.status = BusinessLeadStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def is_submitted_by(self, user_id: UUID) -> bool:
        """Check if lead was submitted by a specific user."""
        return self.submitter_id == user_id
