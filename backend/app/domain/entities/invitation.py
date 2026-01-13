"""Invitation domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import Email, UserRole


@dataclass
class Invitation:
    """Invitation entity for user registration."""

    email: Email
    role: UserRole
    invited_by: UUID  # Admin who created the invitation
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    boond_resource_id: Optional[str] = None  # BoondManager resource ID
    manager_boond_id: Optional[str] = None  # BoondManager manager ID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if invitation has been accepted."""
        return self.accepted_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid (not expired and not accepted)."""
        return not self.is_expired and not self.is_accepted

    @property
    def hours_until_expiry(self) -> int:
        """Get hours remaining until expiry."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds() / 3600)

    def accept(self) -> None:
        """Mark invitation as accepted."""
        if self.is_expired:
            raise ValueError("Cannot accept expired invitation")
        if self.is_accepted:
            raise ValueError("Invitation already accepted")
        self.accepted_at = datetime.utcnow()

    @classmethod
    def create(
        cls,
        email: Email,
        role: UserRole,
        invited_by: UUID,
        token: str,
        validity_hours: int = 48,
        boond_resource_id: Optional[str] = None,
        manager_boond_id: Optional[str] = None,
    ) -> "Invitation":
        """Create a new invitation with default 48h validity."""
        return cls(
            email=email,
            role=role,
            invited_by=invited_by,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=validity_hours),
            boond_resource_id=boond_resource_id,
            manager_boond_id=manager_boond_id,
        )
