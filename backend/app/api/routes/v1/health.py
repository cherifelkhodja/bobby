"""Health check endpoints."""

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, RedisClient, Boond
from app.infrastructure.boond.client import BoondClient

router = APIRouter()


@router.get("/live")
async def liveness():
    """Liveness probe - app is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    db: DbSession,
    redis: RedisClient,
    boond: Boond,
):
    """Readiness probe - app is ready to serve traffic."""
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Redis check
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # Boond check (optional, don't fail if down)
    try:
        if await boond.health_check():
            checks["boond"] = "ok"
        else:
            checks["boond"] = "degraded"
    except Exception:
        checks["boond"] = "degraded"

    # Determine overall status
    critical_checks = {k: v for k, v in checks.items() if k != "boond"}
    all_ok = all(v == "ok" for v in critical_checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
