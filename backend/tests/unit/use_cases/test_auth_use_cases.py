"""Tests for authentication use cases."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.use_cases.auth import (
    ForgotPasswordUseCase,
    LoginCommand,
    LoginUseCase,
    RefreshTokenUseCase,
    RegisterCommand,
    RegisterUserUseCase,
    ResetPasswordUseCase,
    VerifyEmailUseCase,
)
from app.domain.entities import User
from app.domain.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotVerifiedError,
)
from app.domain.value_objects import Email, UserRole


def create_mock_user(**kwargs) -> User:
    """Factory for creating mock users."""
    defaults = {
        "id": uuid4(),
        "email": Email("test@example.com"),
        "first_name": "Test",
        "last_name": "User",
        "password_hash": "hashed_password",
        "role": UserRole.USER,
        "is_verified": True,
        "is_active": True,
    }
    defaults.update(kwargs)
    return User(**defaults)


class TestRegisterUserUseCase:
    """Tests for RegisterUserUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.save = AsyncMock(side_effect=lambda u: u)
        return repo

    @pytest.fixture
    def mock_email_service(self):
        """Create mock email service."""
        service = AsyncMock()
        service.send_verification_email = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_register_success(self, mock_user_repository, mock_email_service):
        """Test successful user registration."""
        use_case = RegisterUserUseCase(mock_user_repository, mock_email_service)
        command = RegisterCommand(
            email="new@example.com",
            password="SecurePassword123!",
            first_name="New",
            last_name="User",
        )

        with patch("app.application.use_cases.auth.create_verification_token", return_value="test-token"):
            with patch("app.application.use_cases.auth.hash_password", return_value="hashed"):
                result = await use_case.execute(command)

        assert result.email == "new@example.com"
        assert result.first_name == "New"
        assert result.last_name == "User"
        assert result.is_verified is False
        mock_user_repository.save.assert_called_once()
        mock_email_service.send_verification_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, mock_user_repository, mock_email_service):
        """Test registration fails when user already exists."""
        existing_user = create_mock_user()
        mock_user_repository.get_by_email = AsyncMock(return_value=existing_user)
        
        use_case = RegisterUserUseCase(mock_user_repository, mock_email_service)
        command = RegisterCommand(
            email="test@example.com",
            password="SecurePassword123!",
            first_name="Test",
            last_name="User",
        )

        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(command)

        mock_user_repository.save.assert_not_called()
        mock_email_service.send_verification_email.assert_not_called()


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_login_success(self, mock_user_repository):
        """Test successful login."""
        user = create_mock_user()
        mock_user_repository.get_by_email = AsyncMock(return_value=user)

        use_case = LoginUseCase(mock_user_repository)
        command = LoginCommand(email="test@example.com", password="correct_password")

        with patch("app.application.use_cases.auth.verify_password", return_value=True):
            with patch("app.application.use_cases.auth.create_access_token", return_value="access"):
                with patch("app.application.use_cases.auth.create_refresh_token", return_value="refresh"):
                    tokens, user_model = await use_case.execute(command)

        assert tokens.access_token == "access"
        assert tokens.refresh_token == "refresh"
        assert user_model.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_user_repository):
        """Test login fails when user not found."""
        mock_user_repository.get_by_email = AsyncMock(return_value=None)

        use_case = LoginUseCase(mock_user_repository)
        command = LoginCommand(email="notfound@example.com", password="password")

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_user_repository):
        """Test login fails with wrong password."""
        user = create_mock_user()
        mock_user_repository.get_by_email = AsyncMock(return_value=user)

        use_case = LoginUseCase(mock_user_repository)
        command = LoginCommand(email="test@example.com", password="wrong_password")

        with patch("app.application.use_cases.auth.verify_password", return_value=False):
            with pytest.raises(InvalidCredentialsError):
                await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_login_user_not_verified(self, mock_user_repository):
        """Test login fails when user is not verified."""
        user = create_mock_user(is_verified=False)
        mock_user_repository.get_by_email = AsyncMock(return_value=user)

        use_case = LoginUseCase(mock_user_repository)
        command = LoginCommand(email="test@example.com", password="password")

        with patch("app.application.use_cases.auth.verify_password", return_value=True):
            with pytest.raises(UserNotVerifiedError):
                await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_login_user_inactive(self, mock_user_repository):
        """Test login fails when user is inactive."""
        user = create_mock_user(is_active=False)
        mock_user_repository.get_by_email = AsyncMock(return_value=user)

        use_case = LoginUseCase(mock_user_repository)
        command = LoginCommand(email="test@example.com", password="password")

        with patch("app.application.use_cases.auth.verify_password", return_value=True):
            with pytest.raises(InvalidCredentialsError):
                await use_case.execute(command)


class TestVerifyEmailUseCase:
    """Tests for VerifyEmailUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_verify_email_success(self, mock_user_repository):
        """Test successful email verification."""
        user = create_mock_user(is_verified=False)
        mock_user_repository.get_by_verification_token = AsyncMock(return_value=user)
        mock_user_repository.save = AsyncMock(side_effect=lambda u: u)

        use_case = VerifyEmailUseCase(mock_user_repository)
        
        result = await use_case.execute("valid-token")

        assert result.is_verified is True
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, mock_user_repository):
        """Test email verification fails with invalid token."""
        mock_user_repository.get_by_verification_token = AsyncMock(return_value=None)

        use_case = VerifyEmailUseCase(mock_user_repository)

        with pytest.raises(InvalidTokenError, match="Verification token not found"):
            await use_case.execute("invalid-token")


class TestForgotPasswordUseCase:
    """Tests for ForgotPasswordUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = AsyncMock()
        repo.save = AsyncMock(side_effect=lambda u: u)
        return repo

    @pytest.fixture
    def mock_email_service(self):
        """Create mock email service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self, mock_user_repository, mock_email_service):
        """Test forgot password sends email when user exists."""
        user = create_mock_user()
        mock_user_repository.get_by_email = AsyncMock(return_value=user)

        use_case = ForgotPasswordUseCase(mock_user_repository, mock_email_service)

        with patch("app.application.use_cases.auth.create_reset_token", return_value="reset-token"):
            result = await use_case.execute("test@example.com")

        assert result is True
        mock_email_service.send_password_reset_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self, mock_user_repository, mock_email_service):
        """Test forgot password returns True even when user not found (security)."""
        mock_user_repository.get_by_email = AsyncMock(return_value=None)

        use_case = ForgotPasswordUseCase(mock_user_repository, mock_email_service)

        result = await use_case.execute("notfound@example.com")

        assert result is True  # Should not reveal if user exists
        mock_email_service.send_password_reset_email.assert_not_called()


class TestResetPasswordUseCase:
    """Tests for ResetPasswordUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = AsyncMock()
        repo.save = AsyncMock(side_effect=lambda u: u)
        return repo

    @pytest.mark.asyncio
    async def test_reset_password_success(self, mock_user_repository):
        """Test successful password reset."""
        user = create_mock_user()
        user.reset_token = "valid-reset-token"
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        mock_user_repository.get_by_reset_token = AsyncMock(return_value=user)

        use_case = ResetPasswordUseCase(mock_user_repository)

        with patch("app.application.use_cases.auth.hash_password", return_value="new_hash"):
            result = await use_case.execute("valid-reset-token", "NewPassword123!")

        assert result is True
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, mock_user_repository):
        """Test password reset fails with invalid token."""
        mock_user_repository.get_by_reset_token = AsyncMock(return_value=None)

        use_case = ResetPasswordUseCase(mock_user_repository)

        with pytest.raises(InvalidTokenError, match="Reset token not found"):
            await use_case.execute("invalid-token", "NewPassword123!")

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, mock_user_repository):
        """Test password reset fails with expired token."""
        user = create_mock_user()
        user.reset_token = "expired-token"
        user.reset_token_expires = datetime.utcnow() - timedelta(hours=1)  # Expired
        mock_user_repository.get_by_reset_token = AsyncMock(return_value=user)

        use_case = ResetPasswordUseCase(mock_user_repository)

        with pytest.raises(InvalidTokenError, match="Reset token has expired"):
            await use_case.execute("expired-token", "NewPassword123!")


class TestRefreshTokenUseCase:
    """Tests for RefreshTokenUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_user_repository):
        """Test successful token refresh."""
        user = create_mock_user()
        mock_user_repository.get_by_id = AsyncMock(return_value=user)

        use_case = RefreshTokenUseCase(mock_user_repository)

        mock_payload = MagicMock()
        mock_payload.sub = str(user.id)

        with patch("app.application.use_cases.auth.decode_token", return_value=mock_payload):
            with patch("app.application.use_cases.auth.create_access_token", return_value="new_access"):
                with patch("app.application.use_cases.auth.create_refresh_token", return_value="new_refresh"):
                    tokens = await use_case.execute("valid-refresh-token")

        assert tokens.access_token == "new_access"
        assert tokens.refresh_token == "new_refresh"

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self, mock_user_repository):
        """Test token refresh fails when user not found."""
        mock_user_repository.get_by_id = AsyncMock(return_value=None)

        use_case = RefreshTokenUseCase(mock_user_repository)

        mock_payload = MagicMock()
        mock_payload.sub = str(uuid4())

        with patch("app.application.use_cases.auth.decode_token", return_value=mock_payload):
            with pytest.raises(InvalidTokenError, match="User not found"):
                await use_case.execute("refresh-token")

    @pytest.mark.asyncio
    async def test_refresh_token_user_inactive(self, mock_user_repository):
        """Test token refresh fails when user is inactive."""
        user = create_mock_user(is_active=False)
        mock_user_repository.get_by_id = AsyncMock(return_value=user)

        use_case = RefreshTokenUseCase(mock_user_repository)

        mock_payload = MagicMock()
        mock_payload.sub = str(user.id)

        with patch("app.application.use_cases.auth.decode_token", return_value=mock_payload):
            with pytest.raises(InvalidTokenError, match="User is deactivated"):
                await use_case.execute("refresh-token")
