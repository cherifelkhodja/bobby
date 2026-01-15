"""Application use cases."""

from app.application.use_cases.auth import (
    LoginUseCase,
    RegisterUserUseCase,
    VerifyEmailUseCase,
    ForgotPasswordUseCase,
    ResetPasswordUseCase,
    RefreshTokenUseCase,
)
from app.application.use_cases.cooptations import (
    CreateCooptationUseCase,
    ListCooptationsUseCase,
    GetCooptationUseCase,
    UpdateCooptationStatusUseCase,
    GetCooptationStatsUseCase,
)
from app.application.use_cases.cv_transformer import (
    TransformCvUseCase,
    GetTemplatesUseCase,
    UploadTemplateUseCase,
    GetTransformationStatsUseCase,
)
from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)
from app.application.use_cases.admin import (
    # Users
    ListUsersUseCase,
    GetUserUseCase,
    UpdateUserUseCase,
    ChangeUserRoleUseCase,
    ActivateUserUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
    # Boond
    GetBoondStatusUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
    GetBoondResourcesUseCase,
)

__all__ = [
    # Auth
    "LoginUseCase",
    "RegisterUserUseCase",
    "VerifyEmailUseCase",
    "ForgotPasswordUseCase",
    "ResetPasswordUseCase",
    "RefreshTokenUseCase",
    # Cooptations
    "CreateCooptationUseCase",
    "ListCooptationsUseCase",
    "GetCooptationUseCase",
    "UpdateCooptationStatusUseCase",
    "GetCooptationStatsUseCase",
    # CV Transformer
    "TransformCvUseCase",
    "GetTemplatesUseCase",
    "UploadTemplateUseCase",
    "GetTransformationStatsUseCase",
    # Opportunities
    "ListOpportunitiesUseCase",
    "SyncOpportunitiesUseCase",
    # Admin - Users
    "ListUsersUseCase",
    "GetUserUseCase",
    "UpdateUserUseCase",
    "ChangeUserRoleUseCase",
    "ActivateUserUseCase",
    "DeactivateUserUseCase",
    "DeleteUserUseCase",
    # Admin - Boond
    "GetBoondStatusUseCase",
    "SyncBoondOpportunitiesUseCase",
    "TestBoondConnectionUseCase",
    "GetBoondResourcesUseCase",
]
