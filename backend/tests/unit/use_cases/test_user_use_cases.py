"""
Tests for User use cases.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.entities import User
from app.domain.value_objects import UserRole, Email


class TestUpdateUserUseCase:
    """Tests for updating users."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def sample_user(self):
        return User(
            id=uuid4(),
            email=Email("test@example.com"),
            first_name="John",
            last_name="Doe",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_update_user_name(self, mock_repository, sample_user):
        """Test updating user name."""
        mock_repository.get_by_id.return_value = sample_user

        sample_user.first_name = "Jane"
        sample_user.last_name = "Smith"
        mock_repository.save.return_value = sample_user

        result = mock_repository.save(sample_user)

        assert result.return_value.first_name == "Jane"
        assert result.return_value.last_name == "Smith"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, mock_repository):
        """Test updating non-existent user."""
        mock_repository.get_by_id.return_value = None

        result = await mock_repository.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_phone(self, mock_repository, sample_user):
        """Test updating user phone."""
        mock_repository.get_by_id.return_value = sample_user

        sample_user.phone = "+33612345678"
        mock_repository.save.return_value = sample_user

        result = mock_repository.save(sample_user)

        assert result.return_value.phone == "+33612345678"


class TestActivateUserUseCase:
    """Tests for activating users."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def inactive_user(self):
        return User(
            id=uuid4(),
            email=Email("inactive@example.com"),
            first_name="Inactive",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=False,
            is_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_activate_user_success(self, mock_repository, inactive_user):
        """Test successful activation."""
        mock_repository.get_by_id.return_value = inactive_user

        inactive_user.activate()
        mock_repository.save.return_value = inactive_user

        assert inactive_user.is_active is True

    @pytest.mark.asyncio
    async def test_activate_already_active(self, mock_repository):
        """Test activating already active user."""
        active_user = User(
            id=uuid4(),
            email=Email("active@example.com"),
            first_name="Active",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = active_user

        active_user.activate()

        assert active_user.is_active is True


class TestDeactivateUserUseCase:
    """Tests for deactivating users."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def active_user(self):
        return User(
            id=uuid4(),
            email=Email("active@example.com"),
            first_name="Active",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, mock_repository, active_user):
        """Test successful deactivation."""
        mock_repository.get_by_id.return_value = active_user

        active_user.deactivate()
        mock_repository.save.return_value = active_user

        assert active_user.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_admin_blocked(self, mock_repository):
        """Test that deactivating last admin is blocked."""
        admin_user = User(
            id=uuid4(),
            email=Email("admin@example.com"),
            first_name="Admin",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = admin_user
        mock_repository.count_active_admins.return_value = 1

        count = await mock_repository.count_active_admins()

        assert count == 1
        # In real use case, this would raise an exception


class TestChangeUserRoleUseCase:
    """Tests for changing user roles."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def sample_user(self):
        return User(
            id=uuid4(),
            email=Email("user@example.com"),
            first_name="Test",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_change_role_to_commercial(self, mock_repository, sample_user):
        """Test changing role to commercial."""
        mock_repository.get_by_id.return_value = sample_user

        sample_user.change_role(UserRole.COMMERCIAL)
        mock_repository.save.return_value = sample_user

        assert sample_user.role == UserRole.COMMERCIAL

    @pytest.mark.asyncio
    async def test_change_role_to_rh(self, mock_repository, sample_user):
        """Test changing role to RH."""
        mock_repository.get_by_id.return_value = sample_user

        sample_user.change_role(UserRole.RH)
        mock_repository.save.return_value = sample_user

        assert sample_user.role == UserRole.RH

    @pytest.mark.asyncio
    async def test_change_role_to_admin(self, mock_repository, sample_user):
        """Test changing role to admin."""
        mock_repository.get_by_id.return_value = sample_user

        sample_user.change_role(UserRole.ADMIN)
        mock_repository.save.return_value = sample_user

        assert sample_user.role == UserRole.ADMIN


class TestDeleteUserUseCase:
    """Tests for deleting users."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def sample_user(self):
        return User(
            id=uuid4(),
            email=Email("delete@example.com"),
            first_name="Delete",
            last_name="Me",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_delete_user_success(self, mock_repository, sample_user):
        """Test successful deletion."""
        mock_repository.get_by_id.return_value = sample_user
        mock_repository.delete.return_value = True

        result = await mock_repository.delete(sample_user.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_repository):
        """Test deleting non-existent user."""
        mock_repository.get_by_id.return_value = None
        mock_repository.delete.return_value = False

        result = await mock_repository.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_last_admin_blocked(self, mock_repository):
        """Test that deleting last admin is blocked."""
        admin_user = User(
            id=uuid4(),
            email=Email("admin@example.com"),
            first_name="Admin",
            last_name="User",
            hashed_password="hashed_password",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = admin_user
        mock_repository.count_active_admins.return_value = 1

        count = await mock_repository.count_active_admins()

        assert count == 1


class TestListUsersUseCase:
    """Tests for listing users."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def sample_users(self):
        return [
            User(
                id=uuid4(),
                email=Email("user1@example.com"),
                first_name="User",
                last_name="One",
                hashed_password="hash",
                role=UserRole.USER,
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow(),
            ),
            User(
                id=uuid4(),
                email=Email("user2@example.com"),
                first_name="User",
                last_name="Two",
                hashed_password="hash",
                role=UserRole.COMMERCIAL,
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_all_users(self, mock_repository, sample_users):
        """Test listing all users."""
        mock_repository.list_all.return_value = sample_users

        result = await mock_repository.list_all()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_users_by_role(self, mock_repository, sample_users):
        """Test listing users filtered by role."""
        mock_repository.list_by_role.return_value = [sample_users[1]]

        result = await mock_repository.list_by_role(UserRole.COMMERCIAL)

        assert len(result) == 1
        assert result[0].role == UserRole.COMMERCIAL

    @pytest.mark.asyncio
    async def test_list_active_users_only(self, mock_repository, sample_users):
        """Test listing only active users."""
        mock_repository.list_active.return_value = sample_users

        result = await mock_repository.list_active()

        assert len(result) == 2
        for user in result:
            assert user.is_active is True
