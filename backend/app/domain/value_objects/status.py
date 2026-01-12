"""Status value objects."""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""

    MEMBER = "member"
    ADMIN = "admin"

    def __str__(self) -> str:
        return self.value


class CooptationStatus(str, Enum):
    """Cooptation status lifecycle."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    INTERVIEW = "interview"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return self.value

    @property
    def is_final(self) -> bool:
        """Check if status is final (no more transitions)."""
        return self in (CooptationStatus.ACCEPTED, CooptationStatus.REJECTED)

    @property
    def display_name(self) -> str:
        """Human-readable status name."""
        names = {
            CooptationStatus.PENDING: "En attente",
            CooptationStatus.IN_REVIEW: "En cours d'examen",
            CooptationStatus.INTERVIEW: "En entretien",
            CooptationStatus.ACCEPTED: "Accepté",
            CooptationStatus.REJECTED: "Refusé",
        }
        return names[self]

    def can_transition_to(self, new_status: "CooptationStatus") -> bool:
        """Check if transition to new status is valid."""
        valid_transitions: dict[CooptationStatus, set[CooptationStatus]] = {
            CooptationStatus.PENDING: {CooptationStatus.IN_REVIEW, CooptationStatus.REJECTED},
            CooptationStatus.IN_REVIEW: {
                CooptationStatus.INTERVIEW,
                CooptationStatus.ACCEPTED,
                CooptationStatus.REJECTED,
            },
            CooptationStatus.INTERVIEW: {CooptationStatus.ACCEPTED, CooptationStatus.REJECTED},
            CooptationStatus.ACCEPTED: set(),
            CooptationStatus.REJECTED: set(),
        }
        return new_status in valid_transitions.get(self, set())
