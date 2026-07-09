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


async def _get_active_user(db: DbSession, authorization: str):
    """Decode the access token, load the user and ensure the account is active.

    Shared loader for the role-based dependencies so the ``is_active`` check
    lives in a single place.

    Raises:
        HTTPException: 401 if not authenticated or user missing, 403 if inactive.
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

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    return user


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
    user = await _get_active_user(db, authorization)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user.id


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
    user = await _get_active_user(db, authorization)

    if user.role not in ("admin", "rh"):
        raise HTTPException(status_code=403, detail="Admin or RH access required")

    return user.id


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
    user = await _get_active_user(db, authorization)

    if user.role not in ("admin", "commercial"):
        raise HTTPException(status_code=403, detail="Admin or Commercial access required")

    return user.id


async def require_adv_or_admin(
    db: DbSession,
    authorization: str = Header(default=""),
) -> UUID:
    """Verify user is ADV or admin and return their ID.

    Args:
        db: Database session.
        authorization: Authorization header (Bearer token).

    Returns:
        User's UUID.

    Raises:
        HTTPException: If not authenticated or not ADV/admin.
    """
    user = await _get_active_user(db, authorization)

    if user.role not in ("admin", "adv"):
        raise HTTPException(status_code=403, detail="Admin or ADV access required")

    return user.id


async def require_contract_access(
    db: DbSession,
    authorization: str = Header(default=""),
) -> tuple[UUID, str, str]:
    """Verify user has contract management access.

    Allowed roles: admin, adv, commercial.
    Returns (user_id, role, email) so route handlers can scope results.

    Returns:
        Tuple of (user_id, user_role, user_email).

    Raises:
        HTTPException: If not authenticated or not authorized.
    """
    user = await _get_active_user(db, authorization)

    if user.role not in ("admin", "adv", "commercial"):
        raise HTTPException(status_code=403, detail="Access denied")

    return user.id, user.role, user.email


# Type aliases for dependencies
AdminUser = Annotated[UUID, Depends(require_admin)]
AdminOrRhUser = Annotated[UUID, Depends(require_admin_or_rh)]
AdminOrCommercialUser = Annotated[UUID, Depends(require_admin_or_commercial)]
AdvOrAdminUser = Annotated[UUID, Depends(require_adv_or_admin)]
ContractAccessUser = Annotated[tuple[UUID, str, str], Depends(require_contract_access)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
