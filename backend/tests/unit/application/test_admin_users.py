"""Unit tests for admin user use cases."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.use_cases.admin.users import (
    ActivateUserUseCase,
    CannotModifyOwnAccountError,
    ChangeUserRoleUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    InvalidRoleError,
    ListUsersUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
    UserNotFoundError,
)
from app.domain.entities import User
from app.domain.value_objects import Email, UserRole


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository."""
    return AsyncMock()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=uuid4(),
        email=Email("test@example.com"),
        first_name="Test",
        last_name="User",
        password_hash="hashed",
        role=UserRole.USER,
        is_verified=True,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    return User(
        id=uuid4(),
        email=Email("admin@example.com"),
        first_name="Admin",
        last_name="User",
        password_hash="hashed",
        role=UserRole.ADMIN,
        is_verified=True,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestListUsersUseCase:
    """Tests for ListUsersUseCase."""

    @pytest.mark.asyncio
    async def test_list_users_success(self, mock_user_repository, sample_user):
        """Test listing users successfully."""
        mock_user_repository.list_all.return_value = [sample_user]
        mock_user_repository.count.return_value = 1

        use_case = ListUsersUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(skip=0, limit=50)

        assert result.total == 1
        assert len(result.users) == 1
        assert result.users[0].email == "test@example.com"
        mock_user_repository.list_all.assert_called_once_with(skip=0, limit=50)

    @pytest.mark.asyncio
    async def test_list_users_empty(self, mock_user_repository):
        """Test listing users when none exist."""
        mock_user_repository.list_all.return_value = []
        mock_user_repository.count.return_value = 0

        use_case = ListUsersUseCase(user_repository=mock_user_repository)
        result = await use_case.execute()

        assert result.total == 0
        assert len(result.users) == 0


class TestGetUserUseCase:
    """Tests for GetUserUseCase."""

    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_user_repository, sample_user):
        """Test getting a user successfully."""
        mock_user_repository.get_by_id.return_value = sample_user

        use_case = GetUserUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(sample_user.id)

        assert result.email == "test@example.com"
        assert result.first_name == "Test"
        mock_user_repository.get_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_user_repository):
        """Test getting a user that doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        use_case = GetUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(uuid4())


class TestUpdateUserUseCase:
    """Tests for UpdateUserUseCase."""

    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_user_repository, sample_user, admin_user):
        """Test updating a user successfully."""
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.save.return_value = sample_user

        use_case = UpdateUserUseCase(user_repository=mock_user_repository)
        command = UpdateUserCommand(first_name="Updated")

        result = await use_case.execute(sample_user.id, command, admin_user.id)

        assert result is not None
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, mock_user_repository, admin_user):
        """Test updating a user that doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        use_case = UpdateUserUseCase(user_repository=mock_user_repository)
        command = UpdateUserCommand(first_name="Updated")

        with pytest.raises(UserNotFoundError):
            await use_case.execute(uuid4(), command, admin_user.id)

    @pytest.mark.asyncio
    async def test_update_own_role_forbidden(self, mock_user_repository, admin_user):
        """Test that admin cannot change their own role."""
        mock_user_repository.get_by_id.return_value = admin_user

        use_case = UpdateUserUseCase(user_repository=mock_user_repository)
        command = UpdateUserCommand(role="user")

        with pytest.raises(CannotModifyOwnAccountError):
            await use_case.execute(admin_user.id, command, admin_user.id)

    @pytest.mark.asyncio
    async def test_update_invalid_role(self, mock_user_repository, sample_user, admin_user):
        """Test updating with an invalid role."""
        mock_user_repository.get_by_id.return_value = sample_user

        use_case = UpdateUserUseCase(user_repository=mock_user_repository)
        command = UpdateUserCommand(role="invalid_role")

        with pytest.raises(InvalidRoleError):
            await use_case.execute(sample_user.id, command, admin_user.id)


class TestChangeUserRoleUseCase:
    """Tests for ChangeUserRoleUseCase."""

    @pytest.mark.asyncio
    async def test_change_role_success(self, mock_user_repository, sample_user, admin_user):
        """Test changing user role successfully."""
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.save.return_value = sample_user

        use_case = ChangeUserRoleUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(sample_user.id, "commercial", admin_user.id)

        assert result is not None
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_role_invalid(self, mock_user_repository, sample_user, admin_user):
        """Test changing to an invalid role."""
        mock_user_repository.get_by_id.return_value = sample_user

        use_case = ChangeUserRoleUseCase(user_repository=mock_user_repository)

        with pytest.raises(InvalidRoleError):
            await use_case.execute(sample_user.id, "superadmin", admin_user.id)

    @pytest.mark.asyncio
    async def test_change_own_role_forbidden(self, mock_user_repository, admin_user):
        """Test that admin cannot change their own role."""
        mock_user_repository.get_by_id.return_value = admin_user

        use_case = ChangeUserRoleUseCase(user_repository=mock_user_repository)

        with pytest.raises(CannotModifyOwnAccountError):
            await use_case.execute(admin_user.id, "user", admin_user.id)


class TestActivateUserUseCase:
    """Tests for ActivateUserUseCase."""

    @pytest.mark.asyncio
    async def test_activate_user_success(self, mock_user_repository, sample_user):
        """Test activating a user successfully."""
        sample_user.is_active = False
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.save.return_value = sample_user

        use_case = ActivateUserUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(sample_user.id)

        assert result is not None
        assert sample_user.is_active is True
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_not_found(self, mock_user_repository):
        """Test activating a user that doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        use_case = ActivateUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(uuid4())


class TestDeactivateUserUseCase:
    """Tests for DeactivateUserUseCase."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, mock_user_repository, sample_user, admin_user):
        """Test deactivating a user successfully."""
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.save.return_value = sample_user

        use_case = DeactivateUserUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(sample_user.id, admin_user.id)

        assert result is not None
        assert sample_user.is_active is False
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_own_account_forbidden(self, mock_user_repository, admin_user):
        """Test that admin cannot deactivate themselves."""
        mock_user_repository.get_by_id.return_value = admin_user

        use_case = DeactivateUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(CannotModifyOwnAccountError):
            await use_case.execute(admin_user.id, admin_user.id)

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, mock_user_repository, admin_user):
        """Test deactivating a user that doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        use_case = DeactivateUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(uuid4(), admin_user.id)


class TestDeleteUserUseCase:
    """Tests for DeleteUserUseCase."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self, mock_user_repository, sample_user, admin_user):
        """Test deleting a user successfully."""
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.delete.return_value = True

        use_case = DeleteUserUseCase(user_repository=mock_user_repository)
        result = await use_case.execute(sample_user.id, admin_user.id)

        assert result is True
        mock_user_repository.delete.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_delete_own_account_forbidden(self, mock_user_repository, admin_user):
        """Test that admin cannot delete themselves."""
        mock_user_repository.get_by_id.return_value = admin_user

        use_case = DeleteUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(CannotModifyOwnAccountError):
            await use_case.execute(admin_user.id, admin_user.id)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_user_repository, admin_user):
        """Test deleting a user that doesn't exist."""
        mock_user_repository.get_by_id.return_value = None

        use_case = DeleteUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(uuid4(), admin_user.id)

    @pytest.mark.asyncio
    async def test_delete_user_failure(self, mock_user_repository, sample_user, admin_user):
        """Test delete operation failure."""
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.delete.return_value = False

        use_case = DeleteUserUseCase(user_repository=mock_user_repository)

        with pytest.raises(RuntimeError):
            await use_case.execute(sample_user.id, admin_user.id)
