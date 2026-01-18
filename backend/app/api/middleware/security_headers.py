"""Security headers middleware.

Adds security headers to all responses to protect against common web vulnerabilities.
Does not rely on external libraries to avoid API compatibility issues.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # X-Frame-Options: prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy: control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # X-Permitted-Cross-Domain-Policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Production-only headers
        if settings.is_production:
            # Strict-Transport-Security: enforce HTTPS (1 year)
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

            # Content-Security-Policy
            frontend_url = settings.FRONTEND_URL or "'self'"
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles for UI frameworks
                "img-src 'self' data: https:",
                "font-src 'self' https: data:",
                f"connect-src 'self' {frontend_url}",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

            # Cache-Control for sensitive responses
            response.headers["Cache-Control"] = "no-store"

        # Permissions-Policy: restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), microphone=(), camera=(), payment=()"
        )

        # Remove server header if present (information disclosure)
        if "server" in response.headers:
            del response.headers["server"]

        return response


# Export for use in main.py
__all__ = ["SecurityHeadersMiddleware"]
