"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.error_handler import error_handler_middleware
from app.api.routes.v1 import (
    admin_router,
    auth_router,
    cooptations_router,
    cv_transformer_router,
    health_router,
    invitations_router,
    opportunities_router,
    published_opportunities_router,
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
    title="Gemini Cooptation API",
    description="API pour l'application de cooptation ESN Gemini",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
)

# Middleware (order matters - CORS must be outermost to handle OPTIONS preflight)
app.middleware("http")(error_handler_middleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
app.include_router(quotation_generator_router, prefix="/api/v1", tags=["Quotation Generator"])
