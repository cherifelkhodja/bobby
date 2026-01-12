"""Admin endpoints for system management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.dependencies import AppSettings, DbSession
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository, UserRepository
from app.infrastructure.security.jwt import decode_token
from app.application.use_cases.opportunities import SyncOpportunitiesUseCase

router = APIRouter()


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


async def require_admin(db: DbSession, authorization: str) -> UUID:
    """Verify user is admin."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_id


@router.get("/boond/status", response_model=BoondStatusResponse)
async def get_boond_status(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get BoondManager connection status."""
    await require_admin(db, authorization)

    configured = bool(settings.BOOND_USERNAME and settings.BOOND_PASSWORD)

    if not configured:
        return BoondStatusResponse(
            connected=False,
            configured=False,
            api_url=settings.BOOND_API_URL,
            error="BoondManager credentials not configured",
        )

    boond_client = BoondClient(settings)

    try:
        connected = await boond_client.health_check()
    except Exception as e:
        return BoondStatusResponse(
            connected=False,
            configured=True,
            api_url=settings.BOOND_API_URL,
            error=str(e),
        )

    # Get opportunities count and last sync time
    opp_repo = OpportunityRepository(db)
    count = await opp_repo.count_active()
    last_sync = await opp_repo.get_last_sync_time()

    return BoondStatusResponse(
        connected=connected,
        configured=True,
        api_url=settings.BOOND_API_URL,
        last_sync=last_sync,
        opportunities_count=count,
    )


@router.post("/boond/sync", response_model=SyncResponse)
async def trigger_boond_sync(
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Trigger synchronization with BoondManager."""
    await require_admin(db, authorization)

    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail="BoondManager credentials not configured",
        )

    boond_client = BoondClient(app_settings)
    opp_repo = OpportunityRepository(db)
    cache_service = CacheService(app_settings)

    use_case = SyncOpportunitiesUseCase(
        boond_client=boond_client,
        opportunity_repository=opp_repo,
        cache_service=cache_service,
    )

    try:
        synced_count = await use_case.execute()
        return SyncResponse(
            success=True,
            synced_count=synced_count,
            message=f"{synced_count} opportunités synchronisées",
        )
    except Exception as e:
        return SyncResponse(
            success=False,
            synced_count=0,
            message=f"Erreur lors de la synchronisation: {str(e)}",
        )


@router.post("/boond/test", response_model=TestConnectionResponse)
async def test_boond_connection(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Test BoondManager connection using GET /candidates."""
    await require_admin(db, authorization)

    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        return TestConnectionResponse(
            success=False,
            status_code=0,
            message="Identifiants BoondManager non configures (BOOND_USERNAME, BOOND_PASSWORD)",
        )

    boond_client = BoondClient(settings)
    result = await boond_client.test_connection()

    return TestConnectionResponse(
        success=result.get("success", False),
        status_code=result.get("status_code", 0),
        message=result.get("message", "Erreur inconnue"),
        candidates_count=result.get("candidates_count"),
    )
