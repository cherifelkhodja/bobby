"""Magic link repository port."""

from typing import Protocol
from uuid import UUID

from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose


class MagicLinkRepositoryPort(Protocol):
    """Port for magic link persistence operations."""

    async def get_by_id(self, link_id: UUID) -> MagicLink | None:
        """Get magic link by ID."""
        ...

    async def get_by_token(self, token: str) -> MagicLink | None:
        """Get magic link by token string."""
        ...

    async def save(self, magic_link: MagicLink) -> MagicLink:
        """Save magic link (create or update)."""
        ...

    async def get_active_by_third_party_and_purpose(
        self,
        third_party_id: UUID,
        purpose: MagicLinkPurpose,
    ) -> MagicLink | None:
        """Get the active (non-revoked, non-expired) magic link for a third party and purpose.

        Returns:
            The active magic link, or None if none exists.
        """
        ...

    async def revoke_all_for_third_party(
        self,
        third_party_id: UUID,
        purpose: MagicLinkPurpose | None = None,
    ) -> int:
        """Revoke all active magic links for a third party.

        Args:
            third_party_id: The third party's ID.
            purpose: Optional filter by purpose. If None, revokes all.

        Returns:
            Number of links revoked.
        """
        ...

    async def revoke_expired(self) -> int:
        """Revoke all expired magic links that haven't been revoked yet.

        Returns:
            Number of links revoked.
        """
        ...
