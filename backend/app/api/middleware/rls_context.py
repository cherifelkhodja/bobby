"""Row Level Security context middleware.

This middleware sets PostgreSQL session variables for RLS policies.
It extracts user info from JWT and sets app.user_id and app.user_role
before each database operation.
"""

from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.security.jwt import decode_token


async def set_rls_context(
    session: AsyncSession,
    user_id: UUID | None,
    user_role: str | None,
) -> None:
    """Set RLS context variables in the database session.

    Args:
        session: SQLAlchemy async session
        user_id: Current user's UUID (or None for unauthenticated)
        user_role: Current user's role (or None for unauthenticated)
    """
    user_id_str = str(user_id) if user_id else ""
    user_role_str = user_role or ""

    # Use the helper function created in migration
    await session.execute(
        text("SELECT set_app_context(:user_id, :user_role)"),
        {"user_id": user_id_str, "user_role": user_role_str},
    )


async def clear_rls_context(session: AsyncSession) -> None:
    """Clear RLS context variables after request completion.

    Args:
        session: SQLAlchemy async session
    """
    await session.execute(text("SELECT clear_app_context()"))


def extract_user_from_request(request: Request) -> tuple[UUID | None, str | None]:
    """Extract user_id and role from request's Authorization header.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (user_id, user_role) or (None, None) if not authenticated
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
        user_id = UUID(payload.get("sub")) if payload.get("sub") else None
        user_role = payload.get("role")
        return user_id, user_role
    except Exception:
        return None, None


class RLSContextManager:
    """Context manager for RLS session setup.

    Usage:
        async with RLSContextManager(session, user_id, user_role):
            # Database operations here are protected by RLS
            result = await session.execute(query)
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        user_role: str | None,
    ):
        self.session = session
        self.user_id = user_id
        self.user_role = user_role

    async def __aenter__(self) -> "RLSContextManager":
        await set_rls_context(self.session, self.user_id, self.user_role)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await clear_rls_context(self.session)


# Dependency for FastAPI routes that need RLS context
async def get_rls_session(
    request: Request,
    session: AsyncSession,
) -> AsyncSession:
    """Get a database session with RLS context set.

    This dependency should be used instead of the regular session
    for endpoints that need RLS protection.

    Usage:
        @router.get("/items")
        async def list_items(
            session: Annotated[AsyncSession, Depends(get_rls_session)]
        ):
            # RLS is active for this session
            ...
    """
    user_id, user_role = extract_user_from_request(request)
    await set_rls_context(session, user_id, user_role)
    return session
