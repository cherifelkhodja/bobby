"""API v1 routes."""

from app.api.routes.v1.auth import router as auth_router
from app.api.routes.v1.users import router as users_router
from app.api.routes.v1.opportunities import router as opportunities_router
from app.api.routes.v1.cooptations import router as cooptations_router
from app.api.routes.v1.health import router as health_router

__all__ = [
    "auth_router",
    "users_router",
    "opportunities_router",
    "cooptations_router",
    "health_router",
]
