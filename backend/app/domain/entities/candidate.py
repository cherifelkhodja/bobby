"""Candidate domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import Email, Phone


@dataclass
class Candidate:
    """Candidate entity representing a proposed candidate."""

    first_name: str
    last_name: str
    email: Email
    civility: str = "M"  # M, Mme
    phone: Optional[Phone] = None
    cv_filename: Optional[str] = None
    cv_path: Optional[str] = None
    daily_rate: Optional[float] = None
    note: Optional[str] = None
    external_id: Optional[str] = None  # BoondManager ID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Get candidate's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Get candidate's display name with civility."""
        return f"{self.civility} {self.first_name} {self.last_name}"

    def update_external_id(self, external_id: str) -> None:
        """Update external BoondManager ID."""
        self.external_id = external_id
        self.updated_at = datetime.utcnow()

    def update_cv(self, filename: str, path: str) -> None:
        """Update CV information."""
        self.cv_filename = filename
        self.cv_path = path
        self.updated_at = datetime.utcnow()
