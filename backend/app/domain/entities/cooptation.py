"""Cooptation domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.domain.entities.candidate import Candidate
from app.domain.entities.opportunity import Opportunity
from app.domain.value_objects import CooptationStatus


@dataclass
class StatusChange:
    """Record of a status change."""

    from_status: CooptationStatus
    to_status: CooptationStatus
    changed_at: datetime = field(default_factory=datetime.utcnow)
    changed_by: Optional[UUID] = None
    comment: Optional[str] = None


@dataclass
class Cooptation:
    """Cooptation entity representing a candidate submission for an opportunity."""

    candidate: Candidate
    opportunity: Opportunity
    submitter_id: UUID
    status: CooptationStatus = CooptationStatus.PENDING
    external_positioning_id: Optional[str] = None  # BoondManager positioning ID
    status_history: list[StatusChange] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_pending(self) -> bool:
        """Check if cooptation is pending."""
        return self.status == CooptationStatus.PENDING

    @property
    def is_final(self) -> bool:
        """Check if cooptation is in final state."""
        return self.status.is_final

    def change_status(
        self,
        new_status: CooptationStatus,
        changed_by: Optional[UUID] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """
        Change cooptation status if transition is valid.

        Returns True if status was changed, False otherwise.
        """
        if not self.status.can_transition_to(new_status):
            return False

        status_change = StatusChange(
            from_status=self.status,
            to_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )
        self.status_history.append(status_change)
        self.status = new_status
        self.updated_at = datetime.utcnow()

        if new_status == CooptationStatus.REJECTED:
            self.rejection_reason = comment

        return True

    def update_external_positioning_id(self, positioning_id: str) -> None:
        """Update external BoondManager positioning ID."""
        self.external_positioning_id = positioning_id
        self.updated_at = datetime.utcnow()

    def get_last_status_change(self) -> Optional[StatusChange]:
        """Get the most recent status change."""
        if not self.status_history:
            return None
        return self.status_history[-1]
