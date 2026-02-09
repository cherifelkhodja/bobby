"""
Cooptation-related domain events.
"""

from uuid import UUID

from ..value_objects import CooptationStatus
from .base import DomainEvent


class CooptationCreatedEvent(DomainEvent):
    """Event raised when a new cooptation is created."""

    cooptation_id: UUID
    candidate_email: str
    candidate_name: str
    opportunity_id: UUID
    opportunity_title: str
    submitter_id: UUID
    submitter_name: str

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)


class CooptationStatusChangedEvent(DomainEvent):
    """Event raised when a cooptation status changes."""

    cooptation_id: UUID
    candidate_email: str
    candidate_name: str
    opportunity_title: str
    old_status: CooptationStatus
    new_status: CooptationStatus
    changed_by: UUID
    comment: str | None = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)


class CooptationAcceptedEvent(DomainEvent):
    """Event raised when a cooptation is accepted."""

    cooptation_id: UUID
    candidate_email: str
    candidate_name: str
    opportunity_id: UUID
    opportunity_title: str
    submitter_id: UUID
    accepted_by: UUID
    comment: str | None = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)


class CooptationRejectedEvent(DomainEvent):
    """Event raised when a cooptation is rejected."""

    cooptation_id: UUID
    candidate_email: str
    candidate_name: str
    opportunity_id: UUID
    opportunity_title: str
    submitter_id: UUID
    rejected_by: UUID
    rejection_reason: str | None = None

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)


class CooptationMovedToInterviewEvent(DomainEvent):
    """Event raised when a candidate moves to interview stage."""

    cooptation_id: UUID
    candidate_email: str
    candidate_name: str
    opportunity_title: str
    submitter_id: UUID
    interview_scheduled_at: str | None = None  # ISO format

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)


class CooptationCandidateContactedEvent(DomainEvent):
    """Event raised when a candidate is contacted about a cooptation."""

    cooptation_id: UUID
    candidate_email: str
    contacted_by: UUID
    contact_method: str  # email, phone, etc.

    def __init__(self, **data):
        super().__init__(aggregate_id=data.get("cooptation_id"), **data)
