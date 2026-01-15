"""API v1 routes."""

from app.api.routes.v1.admin import router as admin_router
from app.api.routes.v1.auth import router as auth_router
from app.api.routes.v1.cooptations import router as cooptations_router
from app.api.routes.v1.cv_transformer import router as cv_transformer_router
from app.api.routes.v1.health import router as health_router
from app.api.routes.v1.invitations import router as invitations_router
from app.api.routes.v1.opportunities import router as opportunities_router
from app.api.routes.v1.published_opportunities import router as published_opportunities_router
from app.api.routes.v1.users import router as users_router

__all__ = [
    "admin_router",
    "auth_router",
    "cooptations_router",
    "cv_transformer_router",
    "health_router",
    "invitations_router",
    "opportunities_router",
    "published_opportunities_router",
    "users_router",
]
