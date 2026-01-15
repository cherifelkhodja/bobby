"""Admin use cases."""

from app.application.use_cases.admin.users import (
    ListUsersUseCase,
    GetUserUseCase,
    UpdateUserUseCase,
    ChangeUserRoleUseCase,
    ActivateUserUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
)
from app.application.use_cases.admin.boond import (
    GetBoondStatusUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
    GetBoondResourcesUseCase,
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
