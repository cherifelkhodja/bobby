"""Invitation repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Invitation
from app.domain.value_objects import Email, UserRole
from app.infrastructure.database.models import InvitationModel


class InvitationRepository:
    """Invitation repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invitation_id: UUID) -> Optional[Invitation]:
        """Get invitation by ID."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[Invitation]:
        """Get pending invitation by email."""
        result = await self.session.execute(
            select(InvitationModel).where(
                InvitationModel.email == email.lower(),
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, invitation: Invitation) -> Invitation:
        """Save invitation (create or update)."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.email = str(invitation.email).lower()
            model.role = str(invitation.role)
            model.token = invitation.token
            model.invited_by = invitation.invited_by
            model.expires_at = invitation.expires_at
            model.accepted_at = invitation.accepted_at
            model.boond_resource_id = invitation.boond_resource_id
            model.manager_boond_id = invitation.manager_boond_id
            model.phone = invitation.phone
            model.first_name = invitation.first_name
            model.last_name = invitation.last_name
        else:
            model = InvitationModel(
                id=invitation.id,
                email=str(invitation.email).lower(),
                role=str(invitation.role),
                token=invitation.token,
                invited_by=invitation.invited_by,
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                boond_resource_id=invitation.boond_resource_id,
                manager_boond_id=invitation.manager_boond_id,
                phone=invitation.phone,
                first_name=invitation.first_name,
                last_name=invitation.last_name,
                created_at=invitation.created_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, invitation_id: UUID) -> bool:
        """Delete invitation by ID."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_pending(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invitation]:
        """List pending (not accepted, not expired) invitations."""
        result = await self.session.execute(
            select(InvitationModel)
            .where(
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
            .offset(skip)
            .limit(limit)
            .order_by(InvitationModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invitation]:
        """List all invitations."""
        result = await self.session.execute(
            select(InvitationModel)
            .offset(skip)
            .limit(limit)
            .order_by(InvitationModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_pending(self) -> int:
        """Count pending invitations."""
        result = await self.session.execute(
            select(func.count(InvitationModel.id)).where(
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar() or 0

    def _to_entity(self, model: InvitationModel) -> Invitation:
        """Convert model to entity."""
        return Invitation(
            id=model.id,
            email=Email(model.email),
            role=UserRole(model.role),
            token=model.token,
            invited_by=model.invited_by,
            expires_at=model.expires_at,
            accepted_at=model.accepted_at,
            boond_resource_id=model.boond_resource_id,
            manager_boond_id=model.manager_boond_id,
            phone=model.phone,
            first_name=model.first_name,
            last_name=model.last_name,
            created_at=model.created_at,
        )
