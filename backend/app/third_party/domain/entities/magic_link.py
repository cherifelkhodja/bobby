"""Magic link domain entity."""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

DEFAULT_EXPIRY_DAYS = 7
MIN_TOKEN_LENGTH = 64


@dataclass
class MagicLink:
    """A secure, time-limited link sent to third parties.

    Used for document upload portals and contract review portals.
    Token is URL-safe, minimum 64 characters.
    """

    third_party_id: UUID
    purpose: MagicLinkPurpose
    email_sent_to: str
    id: UUID = field(default_factory=uuid4)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    contract_request_id: UUID | None = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)
    )
    accessed_at: datetime | None = None
    is_revoked: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        """Check if the magic link is still valid.

        Returns:
            True if the link is not expired and not revoked.
        """
        return not self.is_revoked and datetime.utcnow() < self.expires_at

    def revoke(self) -> None:
        """Revoke this magic link."""
        self.is_revoked = True

    def mark_accessed(self) -> None:
        """Mark this magic link as accessed for the first time."""
        if self.accessed_at is None:
            self.accessed_at = datetime.utcnow()

    @property
    def is_expired(self) -> bool:
        """Check if the magic link has expired."""
        return datetime.utcnow() >= self.expires_at

    @staticmethod
    def generate_token() -> str:
        """Generate a secure URL-safe token.

        Returns:
            A URL-safe token of at least 64 characters.
        """
        return secrets.token_urlsafe(64)
