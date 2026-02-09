"""
Cooptation-related specifications.

Business rules for filtering and validating cooptations.
"""

from datetime import datetime, timedelta
from uuid import UUID

from ..entities import Cooptation
from ..value_objects import CooptationStatus
from .base import Specification


class CooptationByStatusSpecification(Specification[Cooptation]):
    """Specification for cooptations with a specific status."""

    def __init__(self, status: CooptationStatus):
        self._status = status

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return cooptation.status == self._status

    @property
    def status(self) -> CooptationStatus:
        return self._status


class CooptationBySubmitterSpecification(Specification[Cooptation]):
    """Specification for cooptations submitted by a specific user."""

    def __init__(self, submitter_id: UUID):
        self._submitter_id = submitter_id

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return cooptation.submitter_id == self._submitter_id

    @property
    def submitter_id(self) -> UUID:
        return self._submitter_id


class CooptationByOpportunitySpecification(Specification[Cooptation]):
    """Specification for cooptations for a specific opportunity."""

    def __init__(self, opportunity_id: UUID):
        self._opportunity_id = opportunity_id

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return cooptation.opportunity.id == self._opportunity_id

    @property
    def opportunity_id(self) -> UUID:
        return self._opportunity_id


class PendingCooptationsSpecification(Specification[Cooptation]):
    """Specification for pending cooptations."""

    def __init__(self):
        self._status_spec = CooptationByStatusSpecification(CooptationStatus.PENDING)

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return self._status_spec.is_satisfied_by(cooptation)


class InReviewCooptationsSpecification(Specification[Cooptation]):
    """Specification for cooptations currently in review."""

    def __init__(self):
        self._status_spec = CooptationByStatusSpecification(CooptationStatus.IN_REVIEW)

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return self._status_spec.is_satisfied_by(cooptation)


class AcceptedCooptationsSpecification(Specification[Cooptation]):
    """Specification for accepted cooptations."""

    def __init__(self):
        self._status_spec = CooptationByStatusSpecification(CooptationStatus.ACCEPTED)

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return self._status_spec.is_satisfied_by(cooptation)


class RejectedCooptationsSpecification(Specification[Cooptation]):
    """Specification for rejected cooptations."""

    def __init__(self):
        self._status_spec = CooptationByStatusSpecification(CooptationStatus.REJECTED)

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return self._status_spec.is_satisfied_by(cooptation)


class ActiveCooptationsSpecification(Specification[Cooptation]):
    """
    Specification for active cooptations (not rejected or accepted).
    These are cooptations that are still being processed.
    """

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return cooptation.status not in [
            CooptationStatus.ACCEPTED,
            CooptationStatus.REJECTED,
        ]


class RecentCooptationsSpecification(Specification[Cooptation]):
    """
    Specification for cooptations created within a certain time period.
    Default is 30 days.
    """

    def __init__(self, days: int = 30):
        self._cutoff = datetime.utcnow() - timedelta(days=days)

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        if hasattr(cooptation, "created_at") and cooptation.created_at:
            return cooptation.created_at >= self._cutoff
        return False


class CandidateEmailMatchSpecification(Specification[Cooptation]):
    """Specification for cooptations with a candidate email match."""

    def __init__(self, email: str):
        self._email = email.lower()

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return str(cooptation.candidate.email).lower() == self._email


class CanTransitionToStatusSpecification(Specification[Cooptation]):
    """
    Specification for checking if a cooptation can transition to a new status.
    Enforces the cooptation state machine rules.
    """

    def __init__(self, target_status: CooptationStatus):
        self._target_status = target_status

    def is_satisfied_by(self, cooptation: Cooptation) -> bool:
        return cooptation.status.can_transition_to(self._target_status)

    @property
    def target_status(self) -> CooptationStatus:
        return self._target_status
