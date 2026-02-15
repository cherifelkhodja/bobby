"""Status value objects."""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""

    USER = "user"
    COMMERCIAL = "commercial"
    RH = "rh"
    ADV = "adv"
    ADMIN = "admin"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable role name."""
        names = {
            UserRole.USER: "Utilisateur",
            UserRole.COMMERCIAL: "Commercial",
            UserRole.RH: "RH",
            UserRole.ADV: "ADV",
            UserRole.ADMIN: "Administrateur",
        }
        return names[self]

    @property
    def can_manage_users(self) -> bool:
        """Check if role can manage users."""
        return self in (UserRole.ADMIN, UserRole.RH)

    @property
    def can_manage_opportunities(self) -> bool:
        """Check if role can select opportunities to share."""
        return self in (UserRole.ADMIN, UserRole.COMMERCIAL)

    @property
    def can_view_all_cooptations(self) -> bool:
        """Check if role can view all cooptations."""
        return self in (UserRole.ADMIN, UserRole.RH)

    @property
    def can_change_cooptation_status(self) -> bool:
        """Check if role can change cooptation status."""
        return self in (UserRole.ADMIN, UserRole.RH, UserRole.COMMERCIAL)

    @property
    def can_manage_vigilance(self) -> bool:
        """Check if role can manage vigilance documents (validate/reject)."""
        return self in (UserRole.ADMIN, UserRole.ADV)

    @property
    def can_view_vigilance(self) -> bool:
        """Check if role can view vigilance documents and compliance dashboard."""
        return self in (UserRole.ADMIN, UserRole.ADV)

    @property
    def can_manage_contracts(self) -> bool:
        """Check if role can configure contracts and generate drafts."""
        return self in (UserRole.ADMIN, UserRole.ADV)

    @property
    def can_validate_commercial(self) -> bool:
        """Check if role can validate contract requests as commercial."""
        return self in (UserRole.COMMERCIAL,)


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
        return self == CooptationStatus.ACCEPTED

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
            CooptationStatus.REJECTED: {CooptationStatus.PENDING},
        }
        return new_status in valid_transitions.get(self, set())


class OpportunityStatus(str, Enum):
    """Published opportunity status lifecycle."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable status name."""
        names = {
            OpportunityStatus.DRAFT: "Brouillon",
            OpportunityStatus.PUBLISHED: "Publiée",
            OpportunityStatus.CLOSED: "Clôturée",
        }
        return names[self]

    @property
    def is_visible_to_consultants(self) -> bool:
        """Check if opportunity is visible to consultants for cooptation."""
        return self == OpportunityStatus.PUBLISHED
