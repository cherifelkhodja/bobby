"""User read models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserReadModel(BaseModel):
    """User read model for API responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    is_verified: bool
    is_active: bool
    boond_resource_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserListReadModel(BaseModel):
    """Paginated user list read model."""

    model_config = ConfigDict(frozen=True)

    items: list[UserReadModel]
    total: int
    page: int
    page_size: int
