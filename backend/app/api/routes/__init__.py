"""API routes."""

from app.api.routes.v1 import (
    auth_router,
    cooptations_router,
    health_router,
    opportunities_router,
    users_router,
)

__all__ = [
    "auth_router",
    "cooptations_router",
    "health_router",
    "opportunities_router",
    "users_router",
]
