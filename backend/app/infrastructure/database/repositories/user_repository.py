"""User repository implementation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import User
from app.domain.value_objects import Email, UserRole
from app.infrastructure.database.models import UserModel


class UserRepository:
    """User repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_verification_token(self, token: str) -> User | None:
        """Get user by verification token."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.verification_token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_reset_token(self, token: str) -> User | None:
        """Get user by reset token."""
        result = await self.session.execute(select(UserModel).where(UserModel.reset_token == token))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        """Save user (create or update)."""
        result = await self.session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one_or_none()

        if model:
            # Update existing
            model.email = str(user.email).lower()
            model.password_hash = user.password_hash
            model.first_name = user.first_name
            model.last_name = user.last_name
            model.role = str(user.role)
            model.is_verified = user.is_verified
            model.is_active = user.is_active
            model.boond_resource_id = user.boond_resource_id
            model.manager_boond_id = user.manager_boond_id
            model.phone = user.phone
            model.verification_token = user.verification_token
            model.reset_token = user.reset_token
            model.reset_token_expires = user.reset_token_expires
            model.updated_at = datetime.utcnow()
        else:
            # Create new
            model = UserModel(
                id=user.id,
                email=str(user.email).lower(),
                password_hash=user.password_hash,
                first_name=user.first_name,
                last_name=user.last_name,
                role=str(user.role),
                is_verified=user.is_verified,
                is_active=user.is_active,
                boond_resource_id=user.boond_resource_id,
                manager_boond_id=user.manager_boond_id,
                phone=user.phone,
                verification_token=user.verification_token,
                reset_token=user.reset_token,
                reset_token_expires=user.reset_token_expires,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def get_by_boond_resource_id(self, boond_resource_id: str) -> User | None:
        """Get user by BoondManager resource ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.boond_resource_id == boond_resource_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users with pagination."""
        result = await self.session.execute(
            select(UserModel).offset(skip).limit(limit).order_by(UserModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        """Count total users."""
        result = await self.session.execute(select(func.count(UserModel.id)))
        return result.scalar() or 0

    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity."""
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=model.password_hash,
            first_name=model.first_name,
            last_name=model.last_name,
            role=UserRole(model.role),
            is_verified=model.is_verified,
            is_active=model.is_active,
            boond_resource_id=model.boond_resource_id,
            manager_boond_id=model.manager_boond_id,
            phone=model.phone,
            verification_token=model.verification_token,
            reset_token=model.reset_token,
            reset_token_expires=model.reset_token_expires,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
