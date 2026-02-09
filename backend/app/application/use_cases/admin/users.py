"""Admin user management use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities import User
from app.domain.ports import UserRepositoryPort
from app.domain.value_objects import UserRole


class UserNotFoundError(Exception):
    """Raised when user is not found."""

    pass


class CannotModifyOwnAccountError(Exception):
    """Raised when admin tries to modify their own account in forbidden ways."""

    pass


class InvalidRoleError(Exception):
    """Raised when an invalid role is provided."""

    pass


@dataclass
class UserReadModel:
    """Read model for user data."""

    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    phone: str | None
    is_verified: bool
    is_active: bool
    boond_resource_id: str | None
    manager_boond_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserReadModel":
        """Create read model from entity."""
        return cls(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=str(user.role),
            phone=user.phone,
            is_verified=user.is_verified,
            is_active=user.is_active,
            boond_resource_id=user.boond_resource_id,
            manager_boond_id=user.manager_boond_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


@dataclass
class UsersListResult:
    """Result of listing users."""

    users: list[UserReadModel]
    total: int


@dataclass
class UpdateUserCommand:
    """Command for updating user."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role: str | None = None
    boond_resource_id: str | None = None
    manager_boond_id: str | None = None


VALID_ROLES = {"user", "commercial", "rh", "admin"}


class ListUsersUseCase:
    """Use case for listing all users."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(self, skip: int = 0, limit: int = 50) -> UsersListResult:
        """List all users with pagination.

        Args:
            skip: Number of users to skip.
            limit: Maximum number of users to return.

        Returns:
            UsersListResult with users and total count.
        """
        users = await self._user_repository.list_all(skip=skip, limit=limit)
        total = await self._user_repository.count()

        return UsersListResult(
            users=[UserReadModel.from_entity(user) for user in users],
            total=total,
        )


class GetUserUseCase:
    """Use case for getting a single user."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: UUID) -> UserReadModel:
        """Get user by ID.

        Args:
            user_id: User's UUID.

        Returns:
            UserReadModel.

        Raises:
            UserNotFoundError: If user not found.
        """
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        return UserReadModel.from_entity(user)


class UpdateUserUseCase:
    """Use case for updating a user."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(
        self,
        user_id: UUID,
        command: UpdateUserCommand,
        admin_id: UUID,
    ) -> UserReadModel:
        """Update user.

        Args:
            user_id: User's UUID.
            command: Update command with fields to change.
            admin_id: ID of the admin performing the action.

        Returns:
            Updated UserReadModel.

        Raises:
            UserNotFoundError: If user not found.
            CannotModifyOwnAccountError: If admin tries to change own role.
            InvalidRoleError: If invalid role provided.
        """
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # Prevent admin from changing their own role
        if user_id == admin_id and command.role and command.role != str(user.role):
            raise CannotModifyOwnAccountError("Cannot change your own role")

        # Validate role if provided
        if command.role and command.role not in VALID_ROLES:
            raise InvalidRoleError(f"Invalid role: {command.role}")

        # Apply updates
        if command.is_active is not None:
            if command.is_active:
                user.activate()
            else:
                user.deactivate()

        if command.role:
            user.change_role(UserRole(command.role))

        if command.first_name is not None:
            user.first_name = command.first_name

        if command.last_name is not None:
            user.last_name = command.last_name

        if command.phone is not None:
            user.phone = command.phone or None

        if command.boond_resource_id is not None:
            user.boond_resource_id = command.boond_resource_id or None

        if command.manager_boond_id is not None:
            user.manager_boond_id = command.manager_boond_id or None

        updated_user = await self._user_repository.save(user)
        return UserReadModel.from_entity(updated_user)


class ChangeUserRoleUseCase:
    """Use case for changing a user's role."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(
        self,
        user_id: UUID,
        new_role: str,
        admin_id: UUID,
    ) -> UserReadModel:
        """Change user role.

        Args:
            user_id: User's UUID.
            new_role: New role to assign.
            admin_id: ID of the admin performing the action.

        Returns:
            Updated UserReadModel.

        Raises:
            UserNotFoundError: If user not found.
            CannotModifyOwnAccountError: If admin tries to change own role.
            InvalidRoleError: If invalid role provided.
        """
        if new_role not in VALID_ROLES:
            raise InvalidRoleError(f"Invalid role: {new_role}")

        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        if user_id == admin_id:
            raise CannotModifyOwnAccountError("Cannot change your own role")

        user.change_role(UserRole(new_role))
        updated_user = await self._user_repository.save(user)
        return UserReadModel.from_entity(updated_user)


class ActivateUserUseCase:
    """Use case for activating a user account."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: UUID) -> UserReadModel:
        """Activate user account.

        Args:
            user_id: User's UUID.

        Returns:
            Updated UserReadModel.

        Raises:
            UserNotFoundError: If user not found.
        """
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        user.activate()
        updated_user = await self._user_repository.save(user)
        return UserReadModel.from_entity(updated_user)


class DeactivateUserUseCase:
    """Use case for deactivating a user account."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: UUID, admin_id: UUID) -> UserReadModel:
        """Deactivate user account.

        Args:
            user_id: User's UUID.
            admin_id: ID of the admin performing the action.

        Returns:
            Updated UserReadModel.

        Raises:
            UserNotFoundError: If user not found.
            CannotModifyOwnAccountError: If admin tries to deactivate themselves.
        """
        if user_id == admin_id:
            raise CannotModifyOwnAccountError("Cannot deactivate your own account")

        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        user.deactivate()
        updated_user = await self._user_repository.save(user)
        return UserReadModel.from_entity(updated_user)


class DeleteUserUseCase:
    """Use case for permanently deleting a user."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: UUID, admin_id: UUID) -> bool:
        """Delete user permanently.

        Args:
            user_id: User's UUID.
            admin_id: ID of the admin performing the action.

        Returns:
            True if deleted successfully.

        Raises:
            UserNotFoundError: If user not found.
            CannotModifyOwnAccountError: If admin tries to delete themselves.
        """
        if user_id == admin_id:
            raise CannotModifyOwnAccountError("Cannot delete your own account")

        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        deleted = await self._user_repository.delete(user_id)
        if not deleted:
            raise RuntimeError("Failed to delete user")

        return True
