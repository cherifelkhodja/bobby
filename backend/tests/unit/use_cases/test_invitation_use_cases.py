"""Tests for invitation use cases."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.use_cases.invitations import (
    AcceptInvitationCommand,
    AcceptInvitationUseCase,
    CreateInvitationCommand,
    CreateInvitationUseCase,
    DeleteInvitationUseCase,
    InvitationAlreadyAcceptedError,
    InvitationAlreadyExistsError,
    InvitationExpiredError,
    InvitationNotFoundError,
    ListPendingInvitationsUseCase,
    ResendInvitationUseCase,
    UserAlreadyExistsError,
    ValidateInvitationUseCase,
)
from app.domain.entities import Invitation, User
from app.domain.value_objects import Email, UserRole


def create_mock_invitation(accepted: bool = False, **kwargs) -> Invitation:
    """Factory for creating mock invitations.

    Args:
        accepted: If True, sets accepted_at to mark invitation as accepted
        **kwargs: Additional fields to override defaults
    """
    defaults = {
        "id": uuid4(),
        "email": Email("invited@example.com"),
        "role": UserRole.USER,
        "token": "test-token-123",
        "invited_by": uuid4(),
        "expires_at": datetime.utcnow() + timedelta(hours=48),
        "accepted_at": datetime.utcnow() if accepted else None,
    }
    defaults.update(kwargs)
    return Invitation(**defaults)


def create_mock_user(**kwargs) -> User:
    """Factory for creating mock users."""
    defaults = {
        "id": uuid4(),
        "email": Email("user@example.com"),
        "first_name": "Test",
        "last_name": "User",
        "password_hash": "hashed",
        "role": UserRole.USER,
        "is_verified": True,
        "is_active": True,
    }
    defaults.update(kwargs)
    return User(**defaults)


class TestCreateInvitationUseCase:
    """Tests for CreateInvitationUseCase."""

    @pytest.fixture
    def mock_repositories_and_services(self):
        """Create mock repositories and services."""
        return {
            "invitation_repository": AsyncMock(),
            "user_repository": AsyncMock(),
            "email_service": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_create_invitation_success(self, mock_repositories_and_services):
        """Test successful invitation creation."""
        mock_repositories_and_services["user_repository"].get_by_email = AsyncMock(return_value=None)
        mock_repositories_and_services["invitation_repository"].get_by_email = AsyncMock(return_value=None)
        
        invitation = create_mock_invitation()
        mock_repositories_and_services["invitation_repository"].save = AsyncMock(return_value=invitation)
        
        use_case = CreateInvitationUseCase(**mock_repositories_and_services)
        
        command = CreateInvitationCommand(
            email="new@example.com",
            role="user",
            invited_by=uuid4(),
        )
        
        result = await use_case.execute(command)
        
        assert result.email == invitation.email
        mock_repositories_and_services["invitation_repository"].save.assert_called_once()
        mock_repositories_and_services["email_service"].send_invitation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invitation_user_already_exists(self, mock_repositories_and_services):
        """Test invitation creation fails when user already exists."""
        existing_user = create_mock_user()
        mock_repositories_and_services["user_repository"].get_by_email = AsyncMock(return_value=existing_user)
        
        use_case = CreateInvitationUseCase(**mock_repositories_and_services)
        
        command = CreateInvitationCommand(
            email="existing@example.com",
            role="user",
            invited_by=uuid4(),
        )
        
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(command)
        
        mock_repositories_and_services["invitation_repository"].save.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_invitation_already_pending(self, mock_repositories_and_services):
        """Test invitation creation fails when pending invitation exists."""
        mock_repositories_and_services["user_repository"].get_by_email = AsyncMock(return_value=None)
        existing_invitation = create_mock_invitation()
        mock_repositories_and_services["invitation_repository"].get_by_email = AsyncMock(
            return_value=existing_invitation
        )
        
        use_case = CreateInvitationUseCase(**mock_repositories_and_services)
        
        command = CreateInvitationCommand(
            email="invited@example.com",
            role="user",
            invited_by=uuid4(),
        )
        
        with pytest.raises(InvitationAlreadyExistsError):
            await use_case.execute(command)

    @pytest.mark.asyncio
    async def test_create_invitation_with_boond_data(self, mock_repositories_and_services):
        """Test invitation creation with BoondManager data."""
        mock_repositories_and_services["user_repository"].get_by_email = AsyncMock(return_value=None)
        mock_repositories_and_services["invitation_repository"].get_by_email = AsyncMock(return_value=None)
        
        invitation = create_mock_invitation()
        mock_repositories_and_services["invitation_repository"].save = AsyncMock(return_value=invitation)
        
        use_case = CreateInvitationUseCase(**mock_repositories_and_services)
        
        command = CreateInvitationCommand(
            email="boond@example.com",
            role="commercial",
            invited_by=uuid4(),
            boond_resource_id="res-123",
            manager_boond_id="mgr-456",
            phone="+33612345678",
            first_name="Boond",
            last_name="User",
        )
        
        await use_case.execute(command)
        
        mock_repositories_and_services["invitation_repository"].save.assert_called_once()


class TestValidateInvitationUseCase:
    """Tests for ValidateInvitationUseCase."""

    @pytest.fixture
    def mock_invitation_repository(self):
        """Create mock invitation repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_validate_invitation_success(self, mock_invitation_repository):
        """Test successful invitation validation."""
        invitation = create_mock_invitation()
        mock_invitation_repository.get_by_token = AsyncMock(return_value=invitation)
        
        use_case = ValidateInvitationUseCase(mock_invitation_repository)
        
        result = await use_case.execute("test-token-123")
        
        assert result.email == invitation.email
        assert result.role == invitation.role

    @pytest.mark.asyncio
    async def test_validate_invitation_not_found(self, mock_invitation_repository):
        """Test validation fails when invitation not found."""
        mock_invitation_repository.get_by_token = AsyncMock(return_value=None)
        
        use_case = ValidateInvitationUseCase(mock_invitation_repository)
        
        with pytest.raises(InvitationNotFoundError):
            await use_case.execute("invalid-token")

    @pytest.mark.asyncio
    async def test_validate_invitation_already_accepted(self, mock_invitation_repository):
        """Test validation fails when invitation already accepted."""
        invitation = create_mock_invitation(accepted=True)
        mock_invitation_repository.get_by_token = AsyncMock(return_value=invitation)

        use_case = ValidateInvitationUseCase(mock_invitation_repository)

        with pytest.raises(InvitationAlreadyAcceptedError):
            await use_case.execute("test-token")

    @pytest.mark.asyncio
    async def test_validate_invitation_expired(self, mock_invitation_repository):
        """Test validation fails when invitation expired."""
        invitation = create_mock_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        mock_invitation_repository.get_by_token = AsyncMock(return_value=invitation)
        
        use_case = ValidateInvitationUseCase(mock_invitation_repository)
        
        with pytest.raises(InvitationExpiredError):
            await use_case.execute("test-token")


class TestAcceptInvitationUseCase:
    """Tests for AcceptInvitationUseCase."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories."""
        return {
            "invitation_repository": AsyncMock(),
            "user_repository": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_accept_invitation_success(self, mock_repositories):
        """Test successful invitation acceptance."""
        invitation = create_mock_invitation()
        mock_repositories["invitation_repository"].get_by_token = AsyncMock(return_value=invitation)
        mock_repositories["user_repository"].get_by_email = AsyncMock(return_value=None)
        
        user = create_mock_user()
        mock_repositories["user_repository"].save = AsyncMock(return_value=user)
        mock_repositories["invitation_repository"].save = AsyncMock(return_value=invitation)
        
        use_case = AcceptInvitationUseCase(**mock_repositories)
        
        with patch("app.application.use_cases.invitations.hash_password", return_value="hashed"):
            result = await use_case.execute(AcceptInvitationCommand(
                token="test-token",
                first_name="New",
                last_name="User",
                password="SecurePassword123!",
            ))
        
        assert result is not None
        mock_repositories["user_repository"].save.assert_called_once()
        mock_repositories["invitation_repository"].save.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_invitation_not_found(self, mock_repositories):
        """Test acceptance fails when invitation not found."""
        mock_repositories["invitation_repository"].get_by_token = AsyncMock(return_value=None)
        
        use_case = AcceptInvitationUseCase(**mock_repositories)
        
        with pytest.raises(InvitationNotFoundError):
            await use_case.execute(AcceptInvitationCommand(
                token="invalid-token",
                first_name="New",
                last_name="User",
                password="SecurePassword123!",
            ))

    @pytest.mark.asyncio
    async def test_accept_invitation_already_accepted(self, mock_repositories):
        """Test acceptance fails when invitation already accepted."""
        invitation = create_mock_invitation(accepted=True)
        mock_repositories["invitation_repository"].get_by_token = AsyncMock(return_value=invitation)
        
        use_case = AcceptInvitationUseCase(**mock_repositories)
        
        with pytest.raises(InvitationAlreadyAcceptedError):
            await use_case.execute(AcceptInvitationCommand(
                token="test-token",
                first_name="New",
                last_name="User",
                password="SecurePassword123!",
            ))

    @pytest.mark.asyncio
    async def test_accept_invitation_expired(self, mock_repositories):
        """Test acceptance fails when invitation expired."""
        invitation = create_mock_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        mock_repositories["invitation_repository"].get_by_token = AsyncMock(return_value=invitation)
        
        use_case = AcceptInvitationUseCase(**mock_repositories)
        
        with pytest.raises(InvitationExpiredError):
            await use_case.execute(AcceptInvitationCommand(
                token="test-token",
                first_name="New",
                last_name="User",
                password="SecurePassword123!",
            ))

    @pytest.mark.asyncio
    async def test_accept_invitation_user_created_meanwhile(self, mock_repositories):
        """Test acceptance fails if user was created by another process."""
        invitation = create_mock_invitation()
        existing_user = create_mock_user()
        
        mock_repositories["invitation_repository"].get_by_token = AsyncMock(return_value=invitation)
        mock_repositories["user_repository"].get_by_email = AsyncMock(return_value=existing_user)
        
        use_case = AcceptInvitationUseCase(**mock_repositories)
        
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(AcceptInvitationCommand(
                token="test-token",
                first_name="New",
                last_name="User",
                password="SecurePassword123!",
            ))


class TestDeleteInvitationUseCase:
    """Tests for DeleteInvitationUseCase."""

    @pytest.fixture
    def mock_invitation_repository(self):
        """Create mock invitation repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_delete_invitation_success(self, mock_invitation_repository):
        """Test successful invitation deletion."""
        invitation = create_mock_invitation()
        mock_invitation_repository.get_by_id = AsyncMock(return_value=invitation)
        mock_invitation_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteInvitationUseCase(mock_invitation_repository)
        
        result = await use_case.execute(invitation.id)
        
        assert result is True
        mock_invitation_repository.delete.assert_called_once_with(invitation.id)

    @pytest.mark.asyncio
    async def test_delete_invitation_not_found(self, mock_invitation_repository):
        """Test deletion fails when invitation not found."""
        mock_invitation_repository.get_by_id = AsyncMock(return_value=None)
        
        use_case = DeleteInvitationUseCase(mock_invitation_repository)
        
        with pytest.raises(InvitationNotFoundError):
            await use_case.execute(uuid4())

    @pytest.mark.asyncio
    async def test_delete_invitation_already_accepted(self, mock_invitation_repository):
        """Test deletion fails when invitation already accepted."""
        invitation = create_mock_invitation(accepted=True)
        mock_invitation_repository.get_by_id = AsyncMock(return_value=invitation)
        
        use_case = DeleteInvitationUseCase(mock_invitation_repository)
        
        with pytest.raises(InvitationAlreadyAcceptedError):
            await use_case.execute(invitation.id)


class TestResendInvitationUseCase:
    """Tests for ResendInvitationUseCase."""

    @pytest.fixture
    def mock_repositories_and_services(self):
        """Create mock repositories and services."""
        return {
            "invitation_repository": AsyncMock(),
            "email_service": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_resend_invitation_success(self, mock_repositories_and_services):
        """Test successful invitation resend."""
        invitation = create_mock_invitation()
        mock_repositories_and_services["invitation_repository"].get_by_id = AsyncMock(return_value=invitation)
        mock_repositories_and_services["invitation_repository"].save = AsyncMock(
            return_value=create_mock_invitation()
        )
        
        use_case = ResendInvitationUseCase(**mock_repositories_and_services)
        
        result = await use_case.execute(invitation.id)
        
        assert result is not None
        mock_repositories_and_services["email_service"].send_invitation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_resend_invitation_not_found(self, mock_repositories_and_services):
        """Test resend fails when invitation not found."""
        mock_repositories_and_services["invitation_repository"].get_by_id = AsyncMock(return_value=None)
        
        use_case = ResendInvitationUseCase(**mock_repositories_and_services)
        
        with pytest.raises(InvitationNotFoundError):
            await use_case.execute(uuid4())

    @pytest.mark.asyncio
    async def test_resend_invitation_already_accepted(self, mock_repositories_and_services):
        """Test resend fails when invitation already accepted."""
        invitation = create_mock_invitation(accepted=True)
        mock_repositories_and_services["invitation_repository"].get_by_id = AsyncMock(return_value=invitation)
        
        use_case = ResendInvitationUseCase(**mock_repositories_and_services)
        
        with pytest.raises(InvitationAlreadyAcceptedError):
            await use_case.execute(invitation.id)


class TestListPendingInvitationsUseCase:
    """Tests for ListPendingInvitationsUseCase."""

    @pytest.fixture
    def mock_invitation_repository(self):
        """Create mock invitation repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_list_pending_invitations(self, mock_invitation_repository):
        """Test listing pending invitations."""
        invitations = [create_mock_invitation() for _ in range(5)]
        mock_invitation_repository.list_pending = AsyncMock(return_value=invitations)
        
        use_case = ListPendingInvitationsUseCase(mock_invitation_repository)
        
        result = await use_case.execute(skip=0, limit=10)
        
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_pending_invitations_empty(self, mock_invitation_repository):
        """Test listing returns empty when no pending invitations."""
        mock_invitation_repository.list_pending = AsyncMock(return_value=[])
        
        use_case = ListPendingInvitationsUseCase(mock_invitation_repository)
        
        result = await use_case.execute()
        
        assert len(result) == 0
