"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """User response schema."""

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
    created_at: datetime
    updated_at: datetime


class UpdateUserRequest(BaseModel):
    """Update user request."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    boond_resource_id: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=100)
