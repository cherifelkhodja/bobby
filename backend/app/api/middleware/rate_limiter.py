"""Rate limiting middleware using slowapi with Redis backend."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.config import settings


def get_client_ip(request: Request) -> str:
    """Get client IP address, considering proxies."""
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    return get_remote_address(request)


def get_user_identifier(request: Request) -> str:
    """Get user identifier for rate limiting (user_id if authenticated, else IP)."""
    # Try to get user_id from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
    return f"ip:{get_client_ip(request)}"


# Create limiter with Redis backend
# Note: headers_enabled=False because enabling it requires adding Response parameter
# to every rate-limited endpoint, which is more invasive
limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
    headers_enabled=False,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Trop de requêtes. Veuillez réessayer plus tard.",
            "retry_after": exc.detail,
        },
        headers={
            "Retry-After": str(exc.detail),
            "X-RateLimit-Limit": request.state.view_rate_limit if hasattr(request.state, "view_rate_limit") else "unknown",
        },
    )


# Rate limit decorators for common use cases
# Usage: @rate_limit_login on route function
rate_limit_login = limiter.limit("5/minute")  # 5 login attempts per minute
rate_limit_register = limiter.limit("3/minute")  # 3 registrations per minute
rate_limit_forgot_password = limiter.limit("3/minute")  # 3 password reset requests per minute
rate_limit_cv_transform = limiter.limit("10/hour")  # 10 CV transformations per hour (expensive)
rate_limit_api_standard = limiter.limit("100/minute")  # Standard API rate limit
rate_limit_api_heavy = limiter.limit("20/minute")  # Heavy API operations
rate_limit_public = limiter.limit("30/minute")  # Public endpoints (no auth)
