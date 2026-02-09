"""Authentication use cases."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.application.read_models.user import UserReadModel
from app.domain.entities import User
from app.domain.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotVerifiedError,
)
from app.domain.value_objects import Email, UserRole
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.email.sender import EmailService
from app.infrastructure.security.jwt import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_verification_token,
    decode_token,
)
from app.infrastructure.security.password import hash_password, verify_password


@dataclass
class AuthTokens:
    """Authentication tokens response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass
class RegisterCommand:
    """Command for user registration."""

    email: str
    password: str
    first_name: str
    last_name: str
    boond_resource_id: str | None = None


@dataclass
class LoginCommand:
    """Command for user login."""

    email: str
    password: str


class RegisterUserUseCase:
    """Use case for user registration."""

    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
    ) -> None:
        self.user_repository = user_repository
        self.email_service = email_service

    async def execute(self, command: RegisterCommand) -> UserReadModel:
        """Register a new user."""
        # Check if user already exists
        existing = await self.user_repository.get_by_email(command.email)
        if existing:
            raise UserAlreadyExistsError(command.email)

        # Create user entity
        verification_token = create_verification_token()
        user = User(
            email=Email(command.email),
            password_hash=hash_password(command.password),
            first_name=command.first_name,
            last_name=command.last_name,
            role=UserRole.USER,
            is_verified=False,
            verification_token=verification_token,
            boond_resource_id=command.boond_resource_id,
        )

        # Save user
        saved_user = await self.user_repository.save(user)

        # Send verification email
        await self.email_service.send_verification_email(
            to=str(saved_user.email),
            token=verification_token,
            name=saved_user.first_name,
        )

        return self._to_read_model(saved_user)

    def _to_read_model(self, user: User) -> UserReadModel:
        return UserReadModel(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=str(user.role),
            is_verified=user.is_verified,
            is_active=user.is_active,
            boond_resource_id=user.boond_resource_id,
            manager_boond_id=user.manager_boond_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class LoginUseCase:
    """Use case for user login."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, command: LoginCommand) -> tuple[AuthTokens, UserReadModel]:
        """Authenticate user and return tokens."""
        # Find user
        user = await self.user_repository.get_by_email(command.email)
        if not user:
            raise InvalidCredentialsError()

        # Verify password
        if not verify_password(command.password, user.password_hash):
            raise InvalidCredentialsError()

        # Check if verified
        if not user.is_verified:
            raise UserNotVerifiedError()

        # Check if active
        if not user.is_active:
            raise InvalidCredentialsError()

        # Generate tokens
        tokens = AuthTokens(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

        user_read_model = UserReadModel(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=str(user.role),
            is_verified=user.is_verified,
            is_active=user.is_active,
            boond_resource_id=user.boond_resource_id,
            manager_boond_id=user.manager_boond_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return tokens, user_read_model


class VerifyEmailUseCase:
    """Use case for email verification."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, token: str) -> UserReadModel:
        """Verify user email with token."""
        user = await self.user_repository.get_by_verification_token(token)
        if not user:
            raise InvalidTokenError("Verification token not found")

        user.verify_email()
        saved_user = await self.user_repository.save(user)

        return UserReadModel(
            id=str(saved_user.id),
            email=str(saved_user.email),
            first_name=saved_user.first_name,
            last_name=saved_user.last_name,
            full_name=saved_user.full_name,
            role=str(saved_user.role),
            is_verified=saved_user.is_verified,
            is_active=saved_user.is_active,
            boond_resource_id=saved_user.boond_resource_id,
            manager_boond_id=saved_user.manager_boond_id,
            created_at=saved_user.created_at,
            updated_at=saved_user.updated_at,
        )


class ForgotPasswordUseCase:
    """Use case for password reset request."""

    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
    ) -> None:
        self.user_repository = user_repository
        self.email_service = email_service

    async def execute(self, email: str) -> bool:
        """Request password reset. Returns True even if user not found (security)."""
        user = await self.user_repository.get_by_email(email)
        if not user:
            return True  # Don't reveal if user exists

        reset_token = create_reset_token()
        expires = datetime.utcnow() + timedelta(hours=1)
        user.set_reset_token(reset_token, expires)

        await self.user_repository.save(user)

        await self.email_service.send_password_reset_email(
            to=str(user.email),
            token=reset_token,
            name=user.first_name,
        )

        return True


class ResetPasswordUseCase:
    """Use case for password reset."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, token: str, new_password: str) -> bool:
        """Reset password with token."""
        user = await self.user_repository.get_by_reset_token(token)
        if not user:
            raise InvalidTokenError("Reset token not found")

        if not user.is_reset_token_valid():
            raise InvalidTokenError("Reset token has expired")

        user.password_hash = hash_password(new_password)
        user.clear_reset_token()

        await self.user_repository.save(user)
        return True


class RefreshTokenUseCase:
    """Use case for refreshing access token."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, refresh_token: str) -> AuthTokens:
        """Refresh access token."""
        payload = decode_token(refresh_token, expected_type="refresh")

        user = await self.user_repository.get_by_id(UUID(payload.sub))
        if not user:
            raise InvalidTokenError("User not found")

        if not user.is_active:
            raise InvalidTokenError("User is deactivated")

        return AuthTokens(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )
