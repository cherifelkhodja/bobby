"""User domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import Email, UserRole


@dataclass
class User:
    """User entity representing a system user."""

    email: Email
    first_name: str
    last_name: str
    password_hash: str = ""
    role: UserRole = UserRole.MEMBER
    is_verified: bool = False
    is_active: bool = True
    boond_resource_id: Optional[str] = None
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    def verify_email(self) -> None:
        """Mark email as verified."""
        self.is_verified = True
        self.verification_token = None
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def set_reset_token(self, token: str, expires: datetime) -> None:
        """Set password reset token."""
        self.reset_token = token
        self.reset_token_expires = expires
        self.updated_at = datetime.utcnow()

    def clear_reset_token(self) -> None:
        """Clear password reset token."""
        self.reset_token = None
        self.reset_token_expires = None
        self.updated_at = datetime.utcnow()

    def is_reset_token_valid(self) -> bool:
        """Check if reset token is still valid."""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return datetime.utcnow() < self.reset_token_expires
