"""API middleware."""

from app.api.middleware.correlation import CorrelationIdMiddleware, correlation_id_var
from app.api.middleware.error_handler import error_handler_middleware
from app.api.middleware.rate_limiter import (
    limiter,
    rate_limit_api_heavy,
    rate_limit_api_standard,
    rate_limit_cv_transform,
    rate_limit_exceeded_handler,
    rate_limit_forgot_password,
    rate_limit_login,
    rate_limit_public,
    rate_limit_register,
)
from app.api.middleware.rls_context import (
    RLSContextManager,
    clear_rls_context,
    extract_user_from_request,
    get_rls_session,
    set_rls_context,
)
from app.api.middleware.security_headers import SecurityHeadersMiddleware

__all__ = [
    # Correlation
    "CorrelationIdMiddleware",
    "correlation_id_var",
    # Error handling
    "error_handler_middleware",
    # Rate limiting
    "limiter",
    "rate_limit_exceeded_handler",
    "rate_limit_login",
    "rate_limit_register",
    "rate_limit_forgot_password",
    "rate_limit_cv_transform",
    "rate_limit_api_standard",
    "rate_limit_api_heavy",
    "rate_limit_public",
    # Security headers
    "SecurityHeadersMiddleware",
    # RLS context
    "set_rls_context",
    "clear_rls_context",
    "extract_user_from_request",
    "RLSContextManager",
    "get_rls_session",
]
