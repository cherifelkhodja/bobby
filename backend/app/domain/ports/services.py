"""Service port interfaces for external services."""

from typing import Optional, Protocol

from app.domain.entities import Candidate, Opportunity


class BoondServicePort(Protocol):
    """Port for BoondManager API operations."""

    async def get_opportunities(self) -> list[Opportunity]:
        """Fetch opportunities from BoondManager."""
        ...

    async def get_opportunity(self, external_id: str) -> Optional[Opportunity]:
        """Fetch single opportunity from BoondManager."""
        ...

    async def create_candidate(self, candidate: Candidate) -> str:
        """Create candidate in BoondManager. Returns external ID."""
        ...

    async def create_positioning(
        self,
        candidate_external_id: str,
        opportunity_external_id: str,
    ) -> str:
        """Create positioning in BoondManager. Returns positioning ID."""
        ...

    async def health_check(self) -> bool:
        """Check BoondManager API availability."""
        ...


class EmailServicePort(Protocol):
    """Port for email sending operations."""

    async def send_verification_email(self, to: str, token: str, name: str) -> bool:
        """Send email verification link."""
        ...

    async def send_password_reset_email(self, to: str, token: str, name: str) -> bool:
        """Send password reset link."""
        ...

    async def send_magic_link_email(self, to: str, token: str, name: str) -> bool:
        """Send magic link for passwordless login."""
        ...

    async def send_cooptation_confirmation(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
    ) -> bool:
        """Send cooptation submission confirmation."""
        ...

    async def send_cooptation_status_update(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
        new_status: str,
    ) -> bool:
        """Send cooptation status update notification."""
        ...


class CacheServicePort(Protocol):
    """Port for caching operations."""

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> bool:
        """Set value in cache with TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern. Returns count of deleted keys."""
        ...
