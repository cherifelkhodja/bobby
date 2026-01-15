"""Admin API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Boond Schemas
# =============================================================================


class BoondStatusResponse(BaseModel):
    """BoondManager connection status."""

    connected: bool
    configured: bool
    api_url: str
    last_sync: Optional[datetime] = None
    opportunities_count: int = 0
    error: Optional[str] = None


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
    candidates_count: Optional[int] = None


class BoondResourceResponse(BaseModel):
    """BoondManager resource (employee)."""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    agency_id: Optional[str] = None
    agency_name: Optional[str] = None
    resource_type: Optional[int] = None
    resource_type_name: Optional[str] = None
    state: Optional[int] = None
    state_name: Optional[str] = None
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
    phone: Optional[str] = None
    is_verified: bool
    is_active: bool
    boond_resource_id: Optional[str] = None
    manager_boond_id: Optional[str] = None
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

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(
        None,
        description="Role: user, commercial, rh, admin",
        pattern="^(user|commercial|rh|admin)$",
    )
    boond_resource_id: Optional[str] = None
    manager_boond_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ActivateResponse(BaseModel):
    """Activate/deactivate response."""

    message: str
    is_active: bool
