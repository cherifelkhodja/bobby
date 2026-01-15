"""Job application domain entity for Turnover-IT candidates."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class ApplicationStatus(str, Enum):
    """Application status lifecycle (French names for display)."""

    NOUVEAU = "nouveau"
    EN_COURS = "en_cours"
    ENTRETIEN = "entretien"
    ACCEPTE = "accepte"
    REFUSE = "refuse"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable status name in French."""
        names = {
            ApplicationStatus.NOUVEAU: "Nouveau",
            ApplicationStatus.EN_COURS: "En cours",
            ApplicationStatus.ENTRETIEN: "Entretien",
            ApplicationStatus.ACCEPTE: "Accepté",
            ApplicationStatus.REFUSE: "Refusé",
        }
        return names[self]

    @property
    def is_final(self) -> bool:
        """Check if status is final (no more transitions)."""
        return self in (ApplicationStatus.ACCEPTE, ApplicationStatus.REFUSE)

    @property
    def is_positive_final(self) -> bool:
        """Check if status is a positive final outcome."""
        return self == ApplicationStatus.ACCEPTE

    def can_transition_to(self, new_status: "ApplicationStatus") -> bool:
        """Check if transition to new status is valid.

        State machine:
        - NOUVEAU → EN_COURS, REFUSE
        - EN_COURS → ENTRETIEN, ACCEPTE, REFUSE
        - ENTRETIEN → ACCEPTE, REFUSE
        - ACCEPTE → (final)
        - REFUSE → (final)
        """
        valid_transitions: dict[ApplicationStatus, set[ApplicationStatus]] = {
            ApplicationStatus.NOUVEAU: {
                ApplicationStatus.EN_COURS,
                ApplicationStatus.REFUSE,
            },
            ApplicationStatus.EN_COURS: {
                ApplicationStatus.ENTRETIEN,
                ApplicationStatus.ACCEPTE,
                ApplicationStatus.REFUSE,
            },
            ApplicationStatus.ENTRETIEN: {
                ApplicationStatus.ACCEPTE,
                ApplicationStatus.REFUSE,
            },
            ApplicationStatus.ACCEPTE: set(),
            ApplicationStatus.REFUSE: set(),
        }
        return new_status in valid_transitions.get(self, set())


@dataclass
class StatusChange:
    """Record of a status change in application history."""

    from_status: str
    to_status: str
    changed_at: datetime
    changed_by: Optional[UUID] = None
    comment: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_at": self.changed_at.isoformat(),
            "changed_by": str(self.changed_by) if self.changed_by else None,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatusChange":
        """Create from dictionary."""
        return cls(
            from_status=data["from_status"],
            to_status=data["to_status"],
            changed_at=datetime.fromisoformat(data["changed_at"]),
            changed_by=UUID(data["changed_by"]) if data.get("changed_by") else None,
            comment=data.get("comment"),
        )


@dataclass
class MatchingResult:
    """Result of AI-powered CV matching."""

    score: int  # 0-100
    strengths: list[str]  # Points forts
    gaps: list[str]  # Lacunes
    summary: str  # Résumé

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "score": self.score,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MatchingResult":
        """Create from dictionary."""
        return cls(
            score=data.get("score", 0),
            strengths=data.get("strengths", []),
            gaps=data.get("gaps", []),
            summary=data.get("summary", ""),
        )

    @property
    def score_category(self) -> str:
        """Get score category for display.

        Returns:
            'excellent' (≥80), 'good' (50-79), 'low' (<50)
        """
        if self.score >= 80:
            return "excellent"
        elif self.score >= 50:
            return "good"
        else:
            return "low"


@dataclass
class JobApplication:
    """Job application entity for candidates applying via public form.

    This entity manages applications submitted through the public form
    linked to a JobPosting. It includes CV storage, AI matching,
    and status workflow.
    """

    # Required fields from application form
    job_posting_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str  # International format +33...
    job_title: str  # Titre poste souhaité
    tjm_min: float  # TJM minimum
    tjm_max: float  # TJM maximum
    availability_date: date  # Date de disponibilité

    # CV storage
    cv_s3_key: str  # S3/MinIO storage key
    cv_filename: str  # Original filename

    # CV text extraction (for matching)
    cv_text: Optional[str] = None

    # AI matching results
    matching_score: Optional[int] = None  # 0-100
    matching_details: Optional[dict[str, Any]] = None

    # Status workflow
    status: ApplicationStatus = ApplicationStatus.NOUVEAU
    status_history: list[dict] = field(default_factory=list)

    # RH notes
    notes: Optional[str] = None

    # BoondManager integration
    boond_candidate_id: Optional[str] = None

    # Audit fields
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Get candidate's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formatted(self) -> str:
        """Get candidate's full name in 'Prénom NOM' format."""
        return f"{self.first_name} {self.last_name.upper()}"

    @property
    def tjm_range(self) -> str:
        """Get TJM range as formatted string."""
        return f"{int(self.tjm_min)}€ - {int(self.tjm_max)}€"

    @property
    def has_matching_score(self) -> bool:
        """Check if matching score is available."""
        return self.matching_score is not None

    @property
    def matching_result(self) -> Optional[MatchingResult]:
        """Get matching result as structured object."""
        if not self.matching_details:
            return None
        return MatchingResult.from_dict(self.matching_details)

    @property
    def is_created_in_boond(self) -> bool:
        """Check if candidate was created in BoondManager."""
        return self.boond_candidate_id is not None

    def set_matching_score(self, score: int, details: dict[str, Any]) -> None:
        """Set matching score and details from AI analysis.

        Args:
            score: Matching score (0-100, will be clamped)
            details: Matching details (strengths, gaps, summary)
        """
        self.matching_score = max(0, min(100, score))
        self.matching_details = details
        self.updated_at = datetime.utcnow()

    def change_status(
        self,
        new_status: ApplicationStatus,
        changed_by: Optional[UUID] = None,
        comment: Optional[str] = None,
    ) -> None:
        """Change application status with validation.

        Args:
            new_status: Target status
            changed_by: User ID who made the change
            comment: Optional comment for the status change

        Raises:
            ValueError: If transition is not allowed
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(
                f"Transition de statut invalide: {self.status.display_name} → {new_status.display_name}"
            )

        status_change = StatusChange(
            from_status=str(self.status),
            to_status=str(new_status),
            changed_at=datetime.utcnow(),
            changed_by=changed_by,
            comment=comment,
        )

        self.status_history.append(status_change.to_dict())
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def add_note(self, note: str) -> None:
        """Add or replace RH notes.

        Args:
            note: Note content
        """
        self.notes = note
        self.updated_at = datetime.utcnow()

    def mark_created_in_boond(self, boond_candidate_id: str) -> None:
        """Mark application as created in BoondManager.

        Args:
            boond_candidate_id: BoondManager candidate ID
        """
        self.boond_candidate_id = boond_candidate_id
        self.updated_at = datetime.utcnow()

    def set_cv_text(self, cv_text: str) -> None:
        """Set extracted CV text for matching.

        Args:
            cv_text: Extracted text from CV document
        """
        self.cv_text = cv_text
        self.updated_at = datetime.utcnow()

    def get_status_history_objects(self) -> list[StatusChange]:
        """Get status history as StatusChange objects."""
        return [StatusChange.from_dict(h) for h in self.status_history]

    def to_boond_candidate_data(self) -> dict:
        """Convert to data for BoondManager candidate creation.

        Returns:
            Dictionary with candidate data for BoondManager API
        """
        return {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "title": self.job_title,
            "dailyRate": self.tjm_max,  # Use max TJM as daily rate
            "availability": self.availability_date.isoformat(),
        }
