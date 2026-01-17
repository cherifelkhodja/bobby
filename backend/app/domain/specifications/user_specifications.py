"""
User-related specifications.

Business rules for filtering and validating users.
"""

from typing import Optional

from ..entities import User
from ..value_objects import UserRole
from .base import Specification


class IsActiveUserSpecification(Specification[User]):
    """Specification for active users."""

    def is_satisfied_by(self, user: User) -> bool:
        return user.is_active


class IsVerifiedUserSpecification(Specification[User]):
    """Specification for verified users."""

    def is_satisfied_by(self, user: User) -> bool:
        return user.is_verified


class HasRoleSpecification(Specification[User]):
    """
    Specification for users with a specific role.

    Example:
        admin_spec = HasRoleSpecification(UserRole.ADMIN)
        if admin_spec.is_satisfied_by(user):
            print("User is an admin")
    """

    def __init__(self, role: UserRole):
        self._role = role

    def is_satisfied_by(self, user: User) -> bool:
        return user.role == self._role

    @property
    def role(self) -> UserRole:
        return self._role


class HasAnyRoleSpecification(Specification[User]):
    """
    Specification for users with any of the specified roles.

    Example:
        staff_spec = HasAnyRoleSpecification([UserRole.ADMIN, UserRole.RH])
        if staff_spec.is_satisfied_by(user):
            print("User is staff")
    """

    def __init__(self, roles: list[UserRole]):
        self._roles = set(roles)

    def is_satisfied_by(self, user: User) -> bool:
        return user.role in self._roles

    @property
    def roles(self) -> set[UserRole]:
        return self._roles


class UserEmailContainsSpecification(Specification[User]):
    """
    Specification for users whose email contains a substring.
    Case-insensitive search.
    """

    def __init__(self, search_term: str):
        self._search_term = search_term.lower()

    def is_satisfied_by(self, user: User) -> bool:
        return self._search_term in str(user.email).lower()

    @property
    def search_term(self) -> str:
        return self._search_term


class UserNameContainsSpecification(Specification[User]):
    """
    Specification for users whose name contains a substring.
    Searches in first_name, last_name, and full_name.
    Case-insensitive search.
    """

    def __init__(self, search_term: str):
        self._search_term = search_term.lower()

    def is_satisfied_by(self, user: User) -> bool:
        search = self._search_term
        return (
            search in user.first_name.lower() or
            search in user.last_name.lower() or
            search in user.full_name.lower()
        )


class CanPerformActionSpecification(Specification[User]):
    """
    Specification for checking if a user can perform a specific action.
    Used for authorization checks.
    """

    def __init__(self, action: str, resource: Optional[str] = None):
        self._action = action
        self._resource = resource

    def is_satisfied_by(self, user: User) -> bool:
        # Admin can do everything
        if user.role == UserRole.ADMIN:
            return True

        # Define permission matrix
        permissions = {
            UserRole.RH: {
                "view_cooptations": True,
                "update_cooptation_status": True,
                "manage_invitations": True,
                "view_users": True,
                "manage_job_postings": True,
            },
            UserRole.COMMERCIAL: {
                "view_cooptations": True,
                "view_own_opportunities": True,
                "publish_opportunities": True,
            },
            UserRole.USER: {
                "submit_cooptation": True,
                "view_own_cooptations": True,
            },
        }

        role_permissions = permissions.get(user.role, {})
        return role_permissions.get(self._action, False)


# Composite specifications for common use cases
class ActiveAndVerifiedSpecification(Specification[User]):
    """Specification for users who are both active and verified."""

    def __init__(self):
        self._active = IsActiveUserSpecification()
        self._verified = IsVerifiedUserSpecification()

    def is_satisfied_by(self, user: User) -> bool:
        return (
            self._active.is_satisfied_by(user) and
            self._verified.is_satisfied_by(user)
        )


class StaffUserSpecification(Specification[User]):
    """Specification for staff users (admin, rh, commercial)."""

    def __init__(self):
        self._roles = HasAnyRoleSpecification([
            UserRole.ADMIN,
            UserRole.RH,
            UserRole.COMMERCIAL,
        ])

    def is_satisfied_by(self, user: User) -> bool:
        return self._roles.is_satisfied_by(user)
