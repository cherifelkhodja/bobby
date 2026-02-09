"""Admin use cases."""

from app.application.use_cases.admin.boond import (
    GetBoondResourcesUseCase,
    GetBoondStatusUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
)
from app.application.use_cases.admin.users import (
    ActivateUserUseCase,
    ChangeUserRoleUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)

__all__ = [
    # Users
    "ListUsersUseCase",
    "GetUserUseCase",
    "UpdateUserUseCase",
    "ChangeUserRoleUseCase",
    "ActivateUserUseCase",
    "DeactivateUserUseCase",
    "DeleteUserUseCase",
    # Boond
    "GetBoondStatusUseCase",
    "SyncBoondOpportunitiesUseCase",
    "TestBoondConnectionUseCase",
    "GetBoondResourcesUseCase",
]
