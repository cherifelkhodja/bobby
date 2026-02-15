"""PostgreSQL implementation of MagicLinkRepository."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
from app.third_party.infrastructure.models import MagicLinkModel

logger = structlog.get_logger()


class MagicLinkRepository:
    """PostgreSQL-backed magic link repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, link_id: UUID) -> MagicLink | None:
        """Get magic link by ID."""
        result = await self.session.execute(
            select(MagicLinkModel).where(MagicLinkModel.id == link_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> MagicLink | None:
        """Get magic link by token string."""
        result = await self.session.execute(
            select(MagicLinkModel).where(MagicLinkModel.token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, magic_link: MagicLink) -> MagicLink:
        """Save magic link (create or update)."""
        result = await self.session.execute(
            select(MagicLinkModel).where(MagicLinkModel.id == magic_link.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.accessed_at = magic_link.accessed_at
            model.is_revoked = magic_link.is_revoked
        else:
            model = self._to_model(magic_link)
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def get_active_by_third_party_and_purpose(
        self,
        third_party_id: UUID,
        purpose: MagicLinkPurpose,
    ) -> MagicLink | None:
        """Get the active magic link for a third party and purpose."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(MagicLinkModel)
            .where(
                MagicLinkModel.third_party_id == third_party_id,
                MagicLinkModel.purpose == purpose.value,
                MagicLinkModel.is_revoked.is_(False),
                MagicLinkModel.expires_at > now,
            )
            .order_by(MagicLinkModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def revoke_all_for_third_party(
        self,
        third_party_id: UUID,
        purpose: MagicLinkPurpose | None = None,
    ) -> int:
        """Revoke all active magic links for a third party."""
        now = datetime.utcnow()
        stmt = (
            update(MagicLinkModel)
            .where(
                MagicLinkModel.third_party_id == third_party_id,
                MagicLinkModel.is_revoked.is_(False),
                MagicLinkModel.expires_at > now,
            )
            .values(is_revoked=True)
        )

        if purpose:
            stmt = stmt.where(MagicLinkModel.purpose == purpose.value)

        result = await self.session.execute(stmt)
        revoked_count = result.rowcount
        await self.session.flush()

        if revoked_count > 0:
            logger.info(
                "magic_links_revoked",
                third_party_id=str(third_party_id),
                purpose=purpose.value if purpose else "all",
                count=revoked_count,
            )
        return revoked_count

    async def revoke_expired(self) -> int:
        """Revoke all expired magic links that haven't been revoked yet."""
        now = datetime.utcnow()
        stmt = (
            update(MagicLinkModel)
            .where(
                MagicLinkModel.is_revoked.is_(False),
                MagicLinkModel.expires_at <= now,
            )
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        revoked_count = result.rowcount
        await self.session.flush()

        if revoked_count > 0:
            logger.info("expired_magic_links_revoked", count=revoked_count)
        return revoked_count

    def _to_entity(self, model: MagicLinkModel) -> MagicLink:
        """Convert SQLAlchemy model to domain entity."""
        return MagicLink(
            id=model.id,
            token=model.token,
            third_party_id=model.third_party_id,
            contract_request_id=model.contract_request_id,
            purpose=MagicLinkPurpose(model.purpose),
            email_sent_to=model.email_sent_to,
            expires_at=model.expires_at,
            accessed_at=model.accessed_at,
            is_revoked=model.is_revoked,
            created_at=model.created_at,
        )

    def _to_model(self, entity: MagicLink) -> MagicLinkModel:
        """Convert domain entity to SQLAlchemy model."""
        return MagicLinkModel(
            id=entity.id,
            token=entity.token,
            third_party_id=entity.third_party_id,
            contract_request_id=entity.contract_request_id,
            purpose=entity.purpose.value,
            email_sent_to=entity.email_sent_to,
            expires_at=entity.expires_at,
            accessed_at=entity.accessed_at,
            is_revoked=entity.is_revoked,
            created_at=entity.created_at,
        )
