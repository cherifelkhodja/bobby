"""User endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import (
    ChangePasswordRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.dependencies import AppSettings, DbSession
from app.domain.exceptions import InvalidCredentialsError, UserNotFoundError
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.security.jwt import decode_token, TokenPayload
from app.infrastructure.security.password import hash_password, verify_password

router = APIRouter()


async def get_current_user(
    db: DbSession,
    token: str = Depends(lambda: ""),  # Would come from OAuth2
) -> "UserResponse":
    """Get current authenticated user from token."""
    # This is a simplified version - in production would use OAuth2PasswordBearer
    from fastapi.security import OAuth2PasswordBearer

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

    # For now, return a placeholder that requires implementation
    raise HTTPException(status_code=401, detail="Not authenticated")


def get_current_user_id(authorization: str = "") -> UUID:
    """Extract user ID from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    return UUID(payload.sub)


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get current user profile."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(authorization)
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=str(user.email),
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        role=str(user.role),
        is_verified=user.is_verified,
        is_active=user.is_active,
        boond_resource_id=user.boond_resource_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UpdateUserRequest,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Update current user profile."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(authorization)
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name
    if request.boond_resource_id is not None:
        user.boond_resource_id = request.boond_resource_id

    saved_user = await user_repo.save(user)

    return UserResponse(
        id=str(saved_user.id),
        email=str(saved_user.email),
        first_name=saved_user.first_name,
        last_name=saved_user.last_name,
        full_name=saved_user.full_name,
        role=str(saved_user.role),
        is_verified=saved_user.is_verified,
        is_active=saved_user.is_active,
        boond_resource_id=saved_user.boond_resource_id,
        created_at=saved_user.created_at,
        updated_at=saved_user.updated_at,
    )


@router.post("/me/password")
async def change_password(
    request: ChangePasswordRequest,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Change current user password."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = get_current_user_id(authorization)
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    user.password_hash = hash_password(request.new_password)
    await user_repo.save(user)

    return {"message": "Password changed successfully."}
