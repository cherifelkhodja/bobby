"""Opportunity domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Opportunity:
    """Opportunity entity representing a job opportunity from BoondManager."""

    title: str
    reference: str
    external_id: str  # BoondManager ID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    response_deadline: Optional[date] = None
    budget: Optional[float] = None
    manager_name: Optional[str] = None
    manager_email: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    location: Optional[str] = None
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    synced_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_open(self) -> bool:
        """Check if opportunity is still open for submissions."""
        if not self.is_active:
            return False
        if self.response_deadline:
            return date.today() <= self.response_deadline
        return True

    @property
    def days_until_deadline(self) -> Optional[int]:
        """Get days remaining until deadline."""
        if not self.response_deadline:
            return None
        delta = self.response_deadline - date.today()
        return delta.days

    def deactivate(self) -> None:
        """Deactivate opportunity."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate opportunity."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_from_sync(
        self,
        title: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        budget: Optional[float] = None,
        manager_name: Optional[str] = None,
    ) -> None:
        """Update opportunity from BoondManager sync."""
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget
        self.manager_name = manager_name
        self.synced_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
