"""
Health check infrastructure.

Provides health check endpoints for monitoring service status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: str
    version: str
    uptime_seconds: float
    components: dict[str, dict[str, Any]]

    class Config:
        use_enum_values = True


# Type alias for health check functions
HealthCheckFunc = Callable[[], Coroutine[Any, Any, ComponentHealth]]


class HealthChecker:
    """
    Health checker for monitoring service components.

    Registers and executes health checks for various components
    like databases, caches, and external services.

    Example:
        checker = HealthChecker(version="1.0.0")

        @checker.register("database")
        async def check_database():
            # Check database connection
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=5.2
            )

        health = await checker.check_all()
    """

    def __init__(self, version: str = "unknown"):
        self._checks: dict[str, HealthCheckFunc] = {}
        self._version = version
        self._start_time = datetime.utcnow()

    def register(
        self, name: str
    ) -> Callable[[HealthCheckFunc], HealthCheckFunc]:
        """
        Decorator to register a health check function.

        Args:
            name: Component name

        Returns:
            Decorator function
        """

        def decorator(func: HealthCheckFunc) -> HealthCheckFunc:
            self._checks[name] = func
            return func

        return decorator

    def add_check(self, name: str, check: HealthCheckFunc) -> None:
        """
        Add a health check function.

        Args:
            name: Component name
            check: Health check coroutine
        """
        self._checks[name] = check

    async def check_component(self, name: str) -> ComponentHealth:
        """
        Run a single component health check.

        Args:
            name: Component name

        Returns:
            Component health status
        """
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {name}",
            )

        import time

        start = time.perf_counter()
        try:
            result = await self._checks[name]()
            result.latency_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    async def check_all(self) -> HealthResponse:
        """
        Run all registered health checks.

        Returns:
            Overall health response with all component statuses
        """
        components: dict[str, dict[str, Any]] = {}
        overall_status = HealthStatus.HEALTHY

        for name in self._checks:
            result = await self.check_component(name)
            components[name] = {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                **result.metadata,
            }

            # Determine overall status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif (
                result.status == HealthStatus.DEGRADED
                and overall_status != HealthStatus.UNHEALTHY
            ):
                overall_status = HealthStatus.DEGRADED

        uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=self._version,
            uptime_seconds=uptime,
            components=components,
        )

    async def is_healthy(self) -> bool:
        """
        Quick check if the service is healthy.

        Returns:
            True if all components are healthy
        """
        response = await self.check_all()
        return response.status == HealthStatus.HEALTHY


# Default health checker instance
health_checker = HealthChecker()


def create_database_check(get_session: Callable) -> HealthCheckFunc:
    """
    Create a database health check function.

    Args:
        get_session: Function to get database session

    Returns:
        Health check coroutine
    """

    async def check_database() -> ComponentHealth:
        try:
            async with get_session() as session:
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                result.scalar()
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Connection successful",
                )
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)}",
            )

    return check_database


def create_redis_check(redis_client: Any) -> HealthCheckFunc:
    """
    Create a Redis health check function.

    Args:
        redis_client: Redis client instance

    Returns:
        Health check coroutine
    """

    async def check_redis() -> ComponentHealth:
        try:
            await redis_client.ping()
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Connection successful",
            )
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Connection failed: {str(e)}",
            )

    return check_redis


def create_boond_check(boond_client: Any) -> HealthCheckFunc:
    """
    Create a BoondManager API health check function.

    Args:
        boond_client: BoondManager client instance

    Returns:
        Health check coroutine
    """

    async def check_boond() -> ComponentHealth:
        try:
            # Try to get current user info
            is_connected = await boond_client.test_connection()
            if is_connected:
                return ComponentHealth(
                    name="boondmanager",
                    status=HealthStatus.HEALTHY,
                    message="API accessible",
                )
            else:
                return ComponentHealth(
                    name="boondmanager",
                    status=HealthStatus.DEGRADED,
                    message="API not responding correctly",
                )
        except Exception as e:
            return ComponentHealth(
                name="boondmanager",
                status=HealthStatus.DEGRADED,
                message=f"API check failed: {str(e)}",
            )

    return check_boond
