"""Security headers middleware using secure library."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import secure

from app.config import settings


# Configure security headers
# See: https://github.com/TypeError/secure
secure_headers = secure.Secure(
    # Strict-Transport-Security: enforce HTTPS
    hsts=secure.StrictTransportSecurity()
    .max_age(31536000)  # 1 year
    .include_subdomains()
    .preload() if settings.is_production else None,

    # X-Frame-Options: prevent clickjacking
    frame=secure.XFrameOptions().deny(),

    # X-Content-Type-Options: prevent MIME sniffing
    content=secure.XContentTypeOptions(),

    # Referrer-Policy: control referrer information
    referrer=secure.ReferrerPolicy().strict_origin_when_cross_origin(),

    # X-XSS-Protection: legacy XSS protection (for older browsers)
    xss=secure.XXSSProtection().set("1; mode=block"),

    # Content-Security-Policy
    csp=secure.ContentSecurityPolicy()
    .default_src("'self'")
    .script_src("'self'")
    .style_src("'self'", "'unsafe-inline'")  # Allow inline styles for UI frameworks
    .img_src("'self'", "data:", "https:")
    .font_src("'self'", "https:", "data:")
    .connect_src("'self'", settings.FRONTEND_URL)
    .frame_ancestors("'none'")
    .base_uri("'self'")
    .form_action("'self'") if settings.is_production else None,

    # Cache-Control for sensitive responses
    cache=secure.CacheControl().no_store() if settings.is_production else None,

    # Permissions-Policy: restrict browser features
    permissions=secure.PermissionsPolicy()
    .geolocation("self")
    .microphone()  # Deny
    .camera()  # Deny
    .payment()  # Deny
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Set security headers
        secure_headers.framework.fastapi(response)

        # Additional headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Remove server header if present (information disclosure)
        if "server" in response.headers:
            del response.headers["server"]

        return response


# Export configured secure headers for direct use if needed
__all__ = ["SecurityHeadersMiddleware", "secure_headers"]
