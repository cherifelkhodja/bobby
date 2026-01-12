"""Application use cases."""

from app.application.use_cases.auth import (
    LoginUseCase,
    RegisterUserUseCase,
    VerifyEmailUseCase,
    ForgotPasswordUseCase,
    ResetPasswordUseCase,
    RefreshTokenUseCase,
)
from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)
from app.application.use_cases.cooptations import (
    CreateCooptationUseCase,
    ListCooptationsUseCase,
    GetCooptationUseCase,
    UpdateCooptationStatusUseCase,
    GetCooptationStatsUseCase,
)

__all__ = [
    # Auth
    "LoginUseCase",
    "RegisterUserUseCase",
    "VerifyEmailUseCase",
    "ForgotPasswordUseCase",
    "ResetPasswordUseCase",
    "RefreshTokenUseCase",
    # Opportunities
    "ListOpportunitiesUseCase",
    "SyncOpportunitiesUseCase",
    # Cooptations
    "CreateCooptationUseCase",
    "ListCooptationsUseCase",
    "GetCooptationUseCase",
    "UpdateCooptationStatusUseCase",
    "GetCooptationStatsUseCase",
]
