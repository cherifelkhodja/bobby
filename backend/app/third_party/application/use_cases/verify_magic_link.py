"""Use case: Verify a magic link token."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.exceptions import (
    MagicLinkExpiredError,
    MagicLinkNotFoundError,
    MagicLinkRevokedError,
)
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

logger = structlog.get_logger()


@dataclass
class VerifyMagicLinkResult:
    """Result of verifying a magic link."""

    magic_link: MagicLink
    third_party: ThirdParty
    purpose: MagicLinkPurpose
    contract_request_id: UUID | None


class VerifyMagicLinkUseCase:
    """Verify a magic link token and return associated data.

    Checks the token is valid (not expired, not revoked), marks it as
    accessed, and returns the third party and purpose.
    """

    def __init__(
        self,
        magic_link_repository,
        third_party_repository,
    ) -> None:
        self._magic_link_repo = magic_link_repository
        self._third_party_repo = third_party_repository

    async def execute(self, token: str) -> VerifyMagicLinkResult:
        """Execute the use case.

        Args:
            token: The magic link token to verify.

        Returns:
            Verification result with magic link, third party and purpose.

        Raises:
            MagicLinkNotFoundError: If the token does not exist.
            MagicLinkRevokedError: If the link has been revoked.
            MagicLinkExpiredError: If the link has expired.
        """
        magic_link = await self._magic_link_repo.get_by_token(token)
        if not magic_link:
            logger.warning("magic_link_not_found", token_prefix=token[:8])
            raise MagicLinkNotFoundError(token)

        if magic_link.is_revoked:
            logger.warning(
                "magic_link_revoked_access_attempt",
                magic_link_id=str(magic_link.id),
            )
            raise MagicLinkRevokedError(str(magic_link.id))

        if magic_link.is_expired:
            logger.warning(
                "magic_link_expired_access_attempt",
                magic_link_id=str(magic_link.id),
            )
            raise MagicLinkExpiredError(str(magic_link.id))

        # Mark as accessed
        magic_link.mark_accessed()
        await self._magic_link_repo.save(magic_link)

        third_party = await self._third_party_repo.get_by_id(magic_link.third_party_id)
        if not third_party:
            logger.error(
                "magic_link_orphan_third_party",
                magic_link_id=str(magic_link.id),
                third_party_id=str(magic_link.third_party_id),
            )
            raise MagicLinkNotFoundError(token)

        logger.info(
            "magic_link_verified",
            magic_link_id=str(magic_link.id),
            third_party_id=str(third_party.id),
            purpose=magic_link.purpose.value,
        )

        return VerifyMagicLinkResult(
            magic_link=magic_link,
            third_party=third_party,
            purpose=magic_link.purpose,
            contract_request_id=magic_link.contract_request_id,
        )
