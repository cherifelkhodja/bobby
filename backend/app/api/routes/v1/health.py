"""Health check and metrics endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.dependencies import Boond, DbSession, RedisClient
from app.infrastructure.observability.metrics import metrics

router = APIRouter()

# Track application start time
_start_time = datetime.utcnow()


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
    latencies = {}

    # Database check
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    latencies["database_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Redis check
    start = time.perf_counter()
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
    latencies["redis_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Boond check (optional, don't fail if down)
    start = time.perf_counter()
    try:
        if await boond.health_check():
            checks["boond"] = "ok"
        else:
            checks["boond"] = "degraded"
    except Exception:
        checks["boond"] = "degraded"
    latencies["boond_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Determine overall status
    critical_checks = {k: v for k, v in checks.items() if k != "boond"}
    all_ok = all(v == "ok" for v in critical_checks.values())

    uptime = (datetime.utcnow() - _start_time).total_seconds()

    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": round(uptime, 2),
        "checks": checks,
        "latencies": latencies,
    }


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.

    Returns all application metrics in Prometheus text format.
    """
    return Response(
        content=metrics.export_prometheus(),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/metrics/json")
async def get_metrics_json():
    """
    JSON metrics endpoint.

    Returns all application metrics in JSON format for debugging.
    """
    return metrics.export_json()
