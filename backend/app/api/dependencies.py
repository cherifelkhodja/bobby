"""API-specific dependencies for authentication and authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from app.dependencies import DbSession
from app.domain.exceptions import InvalidTokenError
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.security.jwt import decode_token


async def get_current_user_id(
    authorization: str = Header(default=""),
    db: DbSession = None,
) -> UUID:
    """Extract and validate user ID from authorization header.

    Args:
        authorization: Authorization header (Bearer token).
        db: Database session (injected).

    Returns:
        User's UUID.

    Raises:
        HTTPException: If not authenticated.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    try:
        payload = decode_token(token, expected_type="access")
        return UUID(payload.sub)
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def require_admin(
    db: DbSession,
    authorization: str = Header(default=""),
) -> UUID:
    """Verify user is admin and return their ID.

    Args:
        db: Database session.
        authorization: Authorization header (Bearer token).

    Returns:
        Admin user's UUID.

    Raises:
        HTTPException: If not authenticated or not admin.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user_id = UUID(payload.sub)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_id


async def require_admin_or_rh(
    db: DbSession,
    authorization: str = Header(default=""),
) -> UUID:
    """Verify user is admin or RH and return their ID.

    Args:
        db: Database session.
        authorization: Authorization header (Bearer token).

    Returns:
        User's UUID.

    Raises:
        HTTPException: If not authenticated or not admin/RH.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user_id = UUID(payload.sub)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role not in ("admin", "rh"):
        raise HTTPException(status_code=403, detail="Admin or RH access required")

    return user_id


async def require_admin_or_commercial(
    db: DbSession,
    authorization: str = Header(default=""),
) -> UUID:
    """Verify user is admin or commercial and return their ID.

    Args:
        db: Database session.
        authorization: Authorization header (Bearer token).

    Returns:
        User's UUID.

    Raises:
        HTTPException: If not authenticated or not admin/commercial.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user_id = UUID(payload.sub)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role not in ("admin", "commercial"):
        raise HTTPException(status_code=403, detail="Admin or Commercial access required")

    return user_id


# Type aliases for dependencies
AdminUser = Annotated[UUID, Depends(require_admin)]
AdminOrRhUser = Annotated[UUID, Depends(require_admin_or_rh)]
AdminOrCommercialUser = Annotated[UUID, Depends(require_admin_or_commercial)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
