"""Admin API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Boond Schemas
# =============================================================================


class BoondStatusResponse(BaseModel):
    """BoondManager connection status."""

    connected: bool
    configured: bool
    api_url: str
    last_sync: datetime | None = None
    opportunities_count: int = 0
    error: str | None = None


class SyncResponse(BaseModel):
    """Sync operation response."""

    success: bool
    synced_count: int = 0
    message: str


class TestConnectionResponse(BaseModel):
    """Test connection response."""

    success: bool
    status_code: int
    message: str
    candidates_count: int | None = None


class BoondResourceResponse(BaseModel):
    """BoondManager resource (employee)."""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    agency_id: str | None = None
    agency_name: str | None = None
    resource_type: int | None = None
    resource_type_name: str | None = None
    state: int | None = None
    state_name: str | None = None
    suggested_role: str = "user"


class BoondResourcesListResponse(BaseModel):
    """List of resources response."""

    resources: list[BoondResourceResponse]
    total: int


# =============================================================================
# User Management Schemas
# =============================================================================


class UserAdminResponse(BaseModel):
    """User response for admin."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    phone: str | None = None
    is_verified: bool
    is_active: bool
    boond_resource_id: str | None = None
    manager_boond_id: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_read_model(cls, read_model) -> "UserAdminResponse":
        """Create response from use case read model."""
        return cls(
            id=read_model.id,
            email=read_model.email,
            first_name=read_model.first_name,
            last_name=read_model.last_name,
            full_name=read_model.full_name,
            role=read_model.role,
            phone=read_model.phone,
            is_verified=read_model.is_verified,
            is_active=read_model.is_active,
            boond_resource_id=read_model.boond_resource_id,
            manager_boond_id=read_model.manager_boond_id,
            created_at=read_model.created_at.isoformat(),
            updated_at=read_model.updated_at.isoformat(),
        )


class UsersListResponse(BaseModel):
    """List of users response."""

    users: list[UserAdminResponse]
    total: int


class ChangeRoleRequest(BaseModel):
    """Request to change user role."""

    role: str = Field(
        ...,
        description="New role: user, commercial, rh, admin",
        pattern="^(user|commercial|rh|admin)$",
    )


class UpdateUserAdminRequest(BaseModel):
    """Request to update user (admin)."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    role: str | None = Field(
        None,
        description="Role: user, commercial, rh, admin",
        pattern="^(user|commercial|rh|admin)$",
    )
    boond_resource_id: str | None = None
    manager_boond_id: str | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ActivateResponse(BaseModel):
    """Activate/deactivate response."""

    message: str
    is_active: bool


# =============================================================================
# Gemini Settings Schemas
# =============================================================================


class GeminiSettingsResponse(BaseModel):
    """Gemini settings response."""

    current_model: str
    available_models: list[str]
    default_model: str


class GeminiSetModelRequest(BaseModel):
    """Request to set Gemini model."""

    model: str = Field(..., description="Gemini model name")


class GeminiTestResponse(BaseModel):
    """Response from Gemini model test."""

    success: bool
    model: str
    response_time_ms: int
    message: str


# =============================================================================
# CV AI Provider Settings Schemas
# =============================================================================


class CvAiProviderInfo(BaseModel):
    """AI provider info."""

    id: str
    name: str


class CvAiModelInfo(BaseModel):
    """AI model info."""

    id: str
    name: str
    description: str = ""


class CvAiSettingsResponse(BaseModel):
    """CV AI settings response."""

    current_provider: str
    current_model: str
    available_providers: list[CvAiProviderInfo]
    available_models_gemini: list[CvAiModelInfo]
    available_models_claude: list[CvAiModelInfo]


class CvAiSetProviderRequest(BaseModel):
    """Request to set CV AI provider and model."""

    provider: str = Field(..., description="AI provider: 'gemini' or 'claude'")
    model: str = Field(..., description="Model ID for the selected provider")


class CvAiTestResponse(BaseModel):
    """Response from CV AI provider test."""

    success: bool
    provider: str
    model: str
    response_time_ms: int
    message: str


class CvGeneratorBetaSettingsResponse(BaseModel):
    """CV Generator Beta settings response."""

    current_model: str
    available_models: list[CvAiModelInfo]


class CvGeneratorBetaSetModelRequest(BaseModel):
    """Request to set CV Generator Beta model."""

    model: str = Field(..., description="Claude model ID for CV Generator Beta")


# =============================================================================
# Turnover-IT Skills Schemas
# =============================================================================


class TurnoverITSkillResponse(BaseModel):
    """Single Turnover-IT skill."""

    name: str
    slug: str


class TurnoverITSkillsResponse(BaseModel):
    """Turnover-IT skills list with metadata."""

    skills: list[TurnoverITSkillResponse]
    total: int
    last_synced_at: datetime | None = None
    sync_interval_days: int = 30


class TurnoverITSyncResponse(BaseModel):
    """Response from skills sync operation."""

    success: bool
    synced_count: int
    message: str
