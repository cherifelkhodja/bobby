"""API request/response schemas."""

from app.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.api.schemas.cooptation import (
    CooptationListResponse,
    CooptationResponse,
    CooptationStatsResponse,
    CreateCooptationRequest,
    UpdateCooptationStatusRequest,
)
from app.api.schemas.opportunity import (
    OpportunityListResponse,
    OpportunityResponse,
)
from app.api.schemas.user import (
    ChangePasswordRequest,
    UpdateUserRequest,
    UserResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RefreshRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "VerifyEmailRequest",
    # User
    "UserResponse",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    # Opportunity
    "OpportunityResponse",
    "OpportunityListResponse",
    # Cooptation
    "CreateCooptationRequest",
    "CooptationResponse",
    "CooptationListResponse",
    "UpdateCooptationStatusRequest",
    "CooptationStatsResponse",
]
