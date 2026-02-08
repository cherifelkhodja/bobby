"""FastAPI application entry point."""

import warnings

# Suppress FutureWarning from deprecated google-generativeai package
# TODO: Migrate to google.genai (new SDK) to remove this suppression
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.error_handler import error_handler_middleware
from app.api.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.api.routes.v1 import (
    admin_router,
    auth_router,
    cooptations_router,
    cv_transformer_router,
    health_router,
    hr_router,
    invitations_router,
    opportunities_router,
    public_applications_router,
    published_opportunities_router,
    settings_router,
    users_router,
)
from app.quotation_generator.api import router as quotation_generator_router
from app.config import settings
from app.infrastructure.database.connection import engine
from app.infrastructure.database.seed import seed_admin_user
from app.infrastructure.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    configure_logging()

    # Seed admin user in dev/test
    if not settings.is_production:
        await seed_admin_user()

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Bobby API",
    description="API pour l'application Bobby",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Middleware (order matters - outermost runs first)
# 1. CORS must be outermost to handle OPTIONS preflight
# 2. Security headers added to all responses
# 3. Correlation ID for request tracing
# 4. Error handler for consistent error responses
app.middleware("http")(error_handler_middleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# API v1 routes
app.include_router(health_router, prefix="/api/v1/health", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(opportunities_router, prefix="/api/v1/opportunities", tags=["Opportunities"])
app.include_router(cooptations_router, prefix="/api/v1/cooptations", tags=["Cooptations"])
app.include_router(invitations_router, prefix="/api/v1/invitations", tags=["Invitations"])
app.include_router(cv_transformer_router, prefix="/api/v1/cv-transformer", tags=["CV Transformer"])
app.include_router(published_opportunities_router, prefix="/api/v1/published-opportunities", tags=["Published Opportunities"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(hr_router, prefix="/api/v1/hr", tags=["HR"])
app.include_router(public_applications_router, prefix="/api/v1/postuler", tags=["Public Applications"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(quotation_generator_router, prefix="/api/v1", tags=["Quotation Generator"])
