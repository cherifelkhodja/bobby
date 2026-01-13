"""Admin endpoints for system management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.dependencies import AppSettings, DbSession
from app.domain.value_objects import UserRole
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository, UserRepository
from app.infrastructure.security.jwt import decode_token
from app.application.use_cases.opportunities import SyncOpportunitiesUseCase

router = APIRouter()


class BoondStatusResponse(BaseModel):
    """BoondManager connection status."""

    connected: bool
    configured: bool
    api_url: str
    last_sync: Optional[datetime] = None
    opportunities_count: int = 0
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Sync operation response."""

    success: bool
    synced_count: int = 0
    message: str


class TestConnectionResponse(BaseModel):
    """Test connection response."""

    success: bool
    status_code: int
    message: str
    candidates_count: Optional[int] = None


async def require_admin(db: DbSession, authorization: str) -> UUID:
    """Verify user is admin."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_id


@router.get("/boond/status", response_model=BoondStatusResponse)
async def get_boond_status(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get BoondManager connection status."""
    await require_admin(db, authorization)

    configured = bool(settings.BOOND_USERNAME and settings.BOOND_PASSWORD)

    if not configured:
        return BoondStatusResponse(
            connected=False,
            configured=False,
            api_url=settings.BOOND_API_URL,
            error="BoondManager credentials not configured",
        )

    boond_client = BoondClient(settings)

    try:
        connected = await boond_client.health_check()
    except Exception as e:
        return BoondStatusResponse(
            connected=False,
            configured=True,
            api_url=settings.BOOND_API_URL,
            error=str(e),
        )

    # Get opportunities count and last sync time
    opp_repo = OpportunityRepository(db)
    count = await opp_repo.count_active()
    last_sync = await opp_repo.get_last_sync_time()

    return BoondStatusResponse(
        connected=connected,
        configured=True,
        api_url=settings.BOOND_API_URL,
        last_sync=last_sync,
        opportunities_count=count,
    )


@router.post("/boond/sync", response_model=SyncResponse)
async def trigger_boond_sync(
    db: DbSession,
    app_settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Trigger synchronization with BoondManager."""
    await require_admin(db, authorization)

    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail="BoondManager credentials not configured",
        )

    boond_client = BoondClient(app_settings)
    opp_repo = OpportunityRepository(db)
    cache_service = CacheService(app_settings)

    use_case = SyncOpportunitiesUseCase(
        boond_client=boond_client,
        opportunity_repository=opp_repo,
        cache_service=cache_service,
    )

    try:
        synced_count = await use_case.execute()
        return SyncResponse(
            success=True,
            synced_count=synced_count,
            message=f"{synced_count} opportunités synchronisées",
        )
    except Exception as e:
        return SyncResponse(
            success=False,
            synced_count=0,
            message=f"Erreur lors de la synchronisation: {str(e)}",
        )


@router.post("/boond/test", response_model=TestConnectionResponse)
async def test_boond_connection(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Test BoondManager connection using GET /candidates."""
    await require_admin(db, authorization)

    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        return TestConnectionResponse(
            success=False,
            status_code=0,
            message="Identifiants BoondManager non configures (BOOND_USERNAME, BOOND_PASSWORD)",
        )

    boond_client = BoondClient(settings)
    result = await boond_client.test_connection()

    return TestConnectionResponse(
        success=result.get("success", False),
        status_code=result.get("status_code", 0),
        message=result.get("message", "Erreur inconnue"),
        candidates_count=result.get("candidates_count"),
    )


class BoondResourceResponse(BaseModel):
    """BoondManager resource (employee)."""

    id: str
    first_name: str
    last_name: str
    email: str
    manager_id: Optional[str] = None
    agency_id: Optional[str] = None
    agency_name: Optional[str] = None
    resource_type: Optional[int] = None
    resource_type_name: Optional[str] = None
    suggested_role: str = "user"


class BoondResourcesListResponse(BaseModel):
    """List of resources response."""

    resources: list[BoondResourceResponse]
    total: int


@router.get("/boond/resources", response_model=BoondResourcesListResponse)
async def get_boond_resources(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Fetch resources (employees) from BoondManager.

    Only returns resources with state 1 or 2 (active employees).
    """
    await require_admin(db, authorization)

    if not settings.BOOND_USERNAME or not settings.BOOND_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail="BoondManager credentials not configured",
        )

    boond_client = BoondClient(settings)

    try:
        # Fetch resources (includes agency names directly)
        resources = await boond_client.get_resources()

        return BoondResourcesListResponse(
            resources=[
                BoondResourceResponse(
                    id=r["id"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    email=r["email"],
                    manager_id=r.get("manager_id"),
                    agency_id=r.get("agency_id"),
                    agency_name=r.get("agency_name", ""),
                    resource_type=r.get("resource_type"),
                    resource_type_name=r.get("resource_type_name"),
                    suggested_role=r.get("suggested_role", "user"),
                )
                for r in resources
                if r.get("email")  # Only include resources with emails
            ],
            total=len(resources),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch resources: {str(e)}",
        )


# ============================================================================
# User Management Endpoints
# ============================================================================


class UserAdminResponse(BaseModel):
    """User response for admin."""

    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_verified: bool
    is_active: bool
    boond_resource_id: Optional[str] = None
    manager_boond_id: Optional[str] = None
    created_at: str
    updated_at: str


class UsersListResponse(BaseModel):
    """List of users response."""

    users: list[UserAdminResponse]
    total: int


class ChangeRoleRequest(BaseModel):
    """Request to change user role."""

    role: str  # user, commercial, rh, admin


class UpdateUserRequest(BaseModel):
    """Request to update user."""

    is_active: Optional[bool] = None
    role: Optional[str] = None
    boond_resource_id: Optional[str] = None
    manager_boond_id: Optional[str] = None


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    db: DbSession,
    authorization: str = Header(default=""),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all users (admin only)."""
    await require_admin(db, authorization)

    user_repo = UserRepository(db)
    users = await user_repo.list_all(skip=skip, limit=limit)
    total = await user_repo.count()

    return UsersListResponse(
        users=[
            UserAdminResponse(
                id=str(user.id),
                email=str(user.email),
                first_name=user.first_name,
                last_name=user.last_name,
                role=str(user.role),
                is_verified=user.is_verified,
                is_active=user.is_active,
                boond_resource_id=user.boond_resource_id,
                manager_boond_id=user.manager_boond_id,
                created_at=user.created_at.isoformat(),
                updated_at=user.updated_at.isoformat(),
            )
            for user in users
        ],
        total=total,
    )


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Get user details (admin only)."""
    await require_admin(db, authorization)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    return UserAdminResponse(
        id=str(user.id),
        email=str(user.email),
        first_name=user.first_name,
        last_name=user.last_name,
        role=str(user.role),
        is_verified=user.is_verified,
        is_active=user.is_active,
        boond_resource_id=user.boond_resource_id,
        manager_boond_id=user.manager_boond_id,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Update user (admin only)."""
    admin_id = await require_admin(db, authorization)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Prevent admin from changing their own role
    if user_id == admin_id and request.role and request.role != str(user.role):
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas modifier votre propre rôle"
        )

    # Update fields
    if request.is_active is not None:
        if request.is_active:
            user.activate()
        else:
            user.deactivate()

    if request.role:
        if request.role not in ("user", "commercial", "rh", "admin"):
            raise HTTPException(status_code=400, detail="Rôle invalide")
        user.change_role(UserRole(request.role))

    if request.boond_resource_id is not None:
        user.boond_resource_id = request.boond_resource_id or None

    if request.manager_boond_id is not None:
        user.manager_boond_id = request.manager_boond_id or None

    updated_user = await user_repo.save(user)

    return UserAdminResponse(
        id=str(updated_user.id),
        email=str(updated_user.email),
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        role=str(updated_user.role),
        is_verified=updated_user.is_verified,
        is_active=updated_user.is_active,
        boond_resource_id=updated_user.boond_resource_id,
        manager_boond_id=updated_user.manager_boond_id,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )


@router.post("/users/{user_id}/role", response_model=UserAdminResponse)
async def change_user_role(
    user_id: UUID,
    request: ChangeRoleRequest,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Change user role (admin only)."""
    admin_id = await require_admin(db, authorization)

    if request.role not in ("user", "commercial", "rh", "admin"):
        raise HTTPException(status_code=400, detail="Rôle invalide")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Prevent admin from changing their own role
    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas modifier votre propre rôle"
        )

    user.change_role(UserRole(request.role))
    updated_user = await user_repo.save(user)

    return UserAdminResponse(
        id=str(updated_user.id),
        email=str(updated_user.email),
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        role=str(updated_user.role),
        is_verified=updated_user.is_verified,
        is_active=updated_user.is_active,
        boond_resource_id=updated_user.boond_resource_id,
        manager_boond_id=updated_user.manager_boond_id,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Activate a user account (admin only)."""
    await require_admin(db, authorization)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user.activate()
    await user_repo.save(user)

    return {"message": "Utilisateur activé", "is_active": True}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Deactivate a user account (admin only)."""
    admin_id = await require_admin(db, authorization)

    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas désactiver votre propre compte"
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user.deactivate()
    await user_repo.save(user)

    return {"message": "Utilisateur désactivé", "is_active": False}
