"""
Observability middleware for FastAPI.

Provides request logging, metrics collection, and correlation ID tracking.
"""

import time
from typing import Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging import (
    get_correlation_id,
    get_logger,
    set_correlation_id,
    set_user_context,
)
from .metrics import (
    active_connections,
    http_request_duration_seconds,
    http_requests_total,
)

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures each request has a correlation ID.

    The correlation ID is extracted from the X-Correlation-ID header
    or generated if not present. It's added to the response headers
    and made available throughout the request lifecycle.
    """

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.HEADER_NAME)
        if not correlation_id:
            correlation_id = str(uuid4())

        # Set in context
        set_correlation_id(correlation_id)

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[self.HEADER_NAME] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests.

    Logs request start, completion, and any errors with relevant details.
    """

    # Paths to exclude from logging
    EXCLUDE_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Extract request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log request start
        logger.info(
            "Request started",
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Track timing
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Log request completion
            logger.info(
                "Request completed",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return response

        except Exception as e:
            duration = time.perf_counter() - start_time

            # Log error
            logger.error(
                "Request failed",
                method=method,
                path=path,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects HTTP metrics.

    Tracks request counts, durations, and active connections.
    """

    # Paths to exclude from metrics
    EXCLUDE_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip metrics for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        method = request.method
        # Normalize path for metrics (remove IDs)
        path = self._normalize_path(request.url.path)

        # Track active connections
        active_connections.inc()

        # Track timing
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Record metrics
            http_requests_total.inc(
                method=method,
                endpoint=path,
                status=str(response.status_code),
            )
            http_request_duration_seconds.observe(
                duration,
                method=method,
                endpoint=path,
            )

            return response

        except Exception:
            duration = time.perf_counter() - start_time

            # Record error metrics
            http_requests_total.inc(
                method=method,
                endpoint=path,
                status="500",
            )
            http_request_duration_seconds.observe(
                duration,
                method=method,
                endpoint=path,
            )
            raise

        finally:
            active_connections.dec()

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing IDs with placeholders.

        This prevents high cardinality in metrics.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+(/|$)", r"/{id}\1", path)

        return path


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to responses.

    Includes CSP, X-Frame-Options, and other security headers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP header (adjust as needed for your application)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https:",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )

        return response


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts user context from JWT tokens.

    Sets the user ID in the logging context for correlation.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Try to extract user from request state (set by auth dependency)
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            set_user_context(str(user.id))

        return await call_next(request)
