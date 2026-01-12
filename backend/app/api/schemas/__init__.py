"""API request/response schemas."""

from app.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.api.schemas.user import (
    UserResponse,
    UpdateUserRequest,
    ChangePasswordRequest,
)
from app.api.schemas.opportunity import (
    OpportunityResponse,
    OpportunityListResponse,
)
from app.api.schemas.cooptation import (
    CreateCooptationRequest,
    CooptationResponse,
    CooptationListResponse,
    UpdateCooptationStatusRequest,
    CooptationStatsResponse,
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
