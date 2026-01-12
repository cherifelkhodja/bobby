"""JWT token utilities."""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings
from app.domain.exceptions import InvalidTokenError


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    exp: datetime
    type: str  # "access", "refresh", "verification", "reset"
    iat: datetime = datetime.utcnow()


def create_access_token(user_id: UUID) -> str:
    """Create access token for user."""
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expires,
        "type": "access",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """Create refresh token for user."""
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expires,
        "type": "refresh",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_verification_token() -> str:
    """Create email verification token."""
    return secrets.token_urlsafe(32)


def create_reset_token() -> str:
    """Create password reset token."""
    return secrets.token_urlsafe(32)


def decode_token(token: str, expected_type: Optional[str] = None) -> TokenPayload:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string
        expected_type: Expected token type ("access", "refresh", etc.)

    Returns:
        TokenPayload with decoded data

    Raises:
        InvalidTokenError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_type = payload.get("type")
        if expected_type and token_type != expected_type:
            raise InvalidTokenError(f"Expected {expected_type} token, got {token_type}")

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            type=token_type or "unknown",
            iat=datetime.fromtimestamp(payload.get("iat", datetime.utcnow().timestamp())),
        )
    except JWTError as e:
        raise InvalidTokenError(str(e))


def get_token_expiry(token_type: str) -> datetime:
    """Get expiry datetime for token type."""
    if token_type == "access":
        return datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == "refresh":
        return datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    elif token_type == "reset":
        return datetime.utcnow() + timedelta(hours=1)
    elif token_type == "verification":
        return datetime.utcnow() + timedelta(days=7)
    else:
        return datetime.utcnow() + timedelta(hours=1)
