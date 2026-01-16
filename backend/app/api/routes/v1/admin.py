"""Admin endpoints for system management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import AdminUser
from app.api.schemas.admin import (
    ActivateResponse,
    BoondResourceResponse,
    BoondResourcesListResponse,
    BoondStatusResponse,
    ChangeRoleRequest,
    GeminiSetModelRequest,
    GeminiSettingsResponse,
    GeminiTestResponse,
    MessageResponse,
    SyncResponse,
    TestConnectionResponse,
    UpdateUserAdminRequest,
    UserAdminResponse,
    UsersListResponse,
)
from app.application.use_cases.admin import (
    ActivateUserUseCase,
    ChangeUserRoleUseCase,
    DeactivateUserUseCase,
    DeleteUserUseCase,
    GetBoondResourcesUseCase,
    GetBoondStatusUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
    UpdateUserUseCase,
)
from app.application.use_cases.admin.boond import BoondNotConfiguredError
from app.application.use_cases.admin.users import (
    CannotModifyOwnAccountError,
    InvalidRoleError,
    UpdateUserCommand,
    UserNotFoundError,
)
from app.dependencies import AppSettings, DbSession, RedisClient
from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.repositories import OpportunityRepository, UserRepository

router = APIRouter()


# =============================================================================
# Use Case Factory Dependencies
# =============================================================================


def get_list_users_use_case(db: DbSession) -> ListUsersUseCase:
    """Factory for ListUsersUseCase."""
    return ListUsersUseCase(user_repository=UserRepository(db))


def get_get_user_use_case(db: DbSession) -> GetUserUseCase:
    """Factory for GetUserUseCase."""
    return GetUserUseCase(user_repository=UserRepository(db))


def get_update_user_use_case(db: DbSession) -> UpdateUserUseCase:
    """Factory for UpdateUserUseCase."""
    return UpdateUserUseCase(user_repository=UserRepository(db))


def get_change_role_use_case(db: DbSession) -> ChangeUserRoleUseCase:
    """Factory for ChangeUserRoleUseCase."""
    return ChangeUserRoleUseCase(user_repository=UserRepository(db))


def get_activate_user_use_case(db: DbSession) -> ActivateUserUseCase:
    """Factory for ActivateUserUseCase."""
    return ActivateUserUseCase(user_repository=UserRepository(db))


def get_deactivate_user_use_case(db: DbSession) -> DeactivateUserUseCase:
    """Factory for DeactivateUserUseCase."""
    return DeactivateUserUseCase(user_repository=UserRepository(db))


def get_delete_user_use_case(db: DbSession) -> DeleteUserUseCase:
    """Factory for DeleteUserUseCase."""
    return DeleteUserUseCase(user_repository=UserRepository(db))


def get_boond_status_use_case(
    db: DbSession,
    settings: AppSettings,
) -> GetBoondStatusUseCase:
    """Factory for GetBoondStatusUseCase."""
    return GetBoondStatusUseCase(
        settings=settings,
        boond_service=BoondClient(settings),
        opportunity_repository=OpportunityRepository(db),
    )


def get_sync_boond_use_case(
    db: DbSession,
    settings: AppSettings,
) -> SyncBoondOpportunitiesUseCase:
    """Factory for SyncBoondOpportunitiesUseCase."""
    return SyncBoondOpportunitiesUseCase(
        settings=settings,
        boond_service=BoondClient(settings),
        opportunity_repository=OpportunityRepository(db),
        cache_service=CacheService(settings),
    )


def get_test_boond_use_case(settings: AppSettings) -> TestBoondConnectionUseCase:
    """Factory for TestBoondConnectionUseCase."""
    return TestBoondConnectionUseCase(
        settings=settings,
        boond_client=BoondClient(settings),
    )


def get_boond_resources_use_case(settings: AppSettings) -> GetBoondResourcesUseCase:
    """Factory for GetBoondResourcesUseCase."""
    return GetBoondResourcesUseCase(
        settings=settings,
        boond_client=BoondClient(settings),
    )


# Type aliases for use case dependencies
ListUsersUseCaseDep = Annotated[ListUsersUseCase, Depends(get_list_users_use_case)]
GetUserUseCaseDep = Annotated[GetUserUseCase, Depends(get_get_user_use_case)]
UpdateUserUseCaseDep = Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)]
ChangeRoleUseCaseDep = Annotated[ChangeUserRoleUseCase, Depends(get_change_role_use_case)]
ActivateUserUseCaseDep = Annotated[ActivateUserUseCase, Depends(get_activate_user_use_case)]
DeactivateUserUseCaseDep = Annotated[DeactivateUserUseCase, Depends(get_deactivate_user_use_case)]
DeleteUserUseCaseDep = Annotated[DeleteUserUseCase, Depends(get_delete_user_use_case)]
BoondStatusUseCaseDep = Annotated[GetBoondStatusUseCase, Depends(get_boond_status_use_case)]
SyncBoondUseCaseDep = Annotated[SyncBoondOpportunitiesUseCase, Depends(get_sync_boond_use_case)]
TestBoondUseCaseDep = Annotated[TestBoondConnectionUseCase, Depends(get_test_boond_use_case)]
BoondResourcesUseCaseDep = Annotated[GetBoondResourcesUseCase, Depends(get_boond_resources_use_case)]


# =============================================================================
# BoondManager Endpoints
# =============================================================================


@router.get("/boond/status", response_model=BoondStatusResponse)
async def get_boond_status(
    admin_id: AdminUser,
    use_case: BoondStatusUseCaseDep,
):
    """Get BoondManager connection status."""
    result = await use_case.execute()

    return BoondStatusResponse(
        connected=result.connected,
        configured=result.configured,
        api_url=result.api_url,
        last_sync=result.last_sync,
        opportunities_count=result.opportunities_count,
        error=result.error,
    )


@router.post("/boond/sync", response_model=SyncResponse)
async def trigger_boond_sync(
    admin_id: AdminUser,
    use_case: SyncBoondUseCaseDep,
):
    """Trigger synchronization with BoondManager."""
    try:
        result = await use_case.execute()
        return SyncResponse(
            success=result.success,
            synced_count=result.synced_count,
            message=result.message,
        )
    except BoondNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/boond/test", response_model=TestConnectionResponse)
async def test_boond_connection(
    admin_id: AdminUser,
    use_case: TestBoondUseCaseDep,
):
    """Test BoondManager connection using GET /candidates."""
    result = await use_case.execute()

    return TestConnectionResponse(
        success=result.success,
        status_code=result.status_code,
        message=result.message,
        candidates_count=result.candidates_count,
    )


@router.get("/boond/resources", response_model=BoondResourcesListResponse)
async def get_boond_resources(
    admin_id: AdminUser,
    use_case: BoondResourcesUseCaseDep,
):
    """Fetch resources (employees) from BoondManager."""
    try:
        result = await use_case.execute()

        return BoondResourcesListResponse(
            resources=[
                BoondResourceResponse(
                    id=r.id,
                    first_name=r.first_name,
                    last_name=r.last_name,
                    email=r.email,
                    phone=r.phone,
                    manager_id=r.manager_id,
                    manager_name=r.manager_name,
                    agency_id=r.agency_id,
                    agency_name=r.agency_name or "",
                    resource_type=r.resource_type,
                    resource_type_name=r.resource_type_name,
                    state=r.state,
                    state_name=r.state_name,
                    suggested_role=r.suggested_role,
                )
                for r in result.resources
            ],
            total=result.total,
        )
    except BoondNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resources: {str(e)}")


# =============================================================================
# User Management Endpoints
# =============================================================================


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    admin_id: AdminUser,
    use_case: ListUsersUseCaseDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all users (admin only)."""
    result = await use_case.execute(skip=skip, limit=limit)

    return UsersListResponse(
        users=[UserAdminResponse.from_read_model(u) for u in result.users],
        total=result.total,
    )


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: UUID,
    admin_id: AdminUser,
    use_case: GetUserUseCaseDep,
):
    """Get user details (admin only)."""
    try:
        result = await use_case.execute(user_id)
        return UserAdminResponse.from_read_model(result)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserAdminRequest,
    admin_id: AdminUser,
    use_case: UpdateUserUseCaseDep,
):
    """Update user (admin only)."""
    try:
        command = UpdateUserCommand(
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            is_active=request.is_active,
            role=request.role,
            boond_resource_id=request.boond_resource_id,
            manager_boond_id=request.manager_boond_id,
        )
        result = await use_case.execute(user_id, command, admin_id)
        return UserAdminResponse.from_read_model(result)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    except CannotModifyOwnAccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidRoleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/role", response_model=UserAdminResponse)
async def change_user_role(
    user_id: UUID,
    request: ChangeRoleRequest,
    admin_id: AdminUser,
    use_case: ChangeRoleUseCaseDep,
):
    """Change user role (admin only)."""
    try:
        result = await use_case.execute(user_id, request.role, admin_id)
        return UserAdminResponse.from_read_model(result)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    except CannotModifyOwnAccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidRoleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/activate", response_model=ActivateResponse)
async def activate_user(
    user_id: UUID,
    admin_id: AdminUser,
    use_case: ActivateUserUseCaseDep,
):
    """Activate a user account (admin only)."""
    try:
        await use_case.execute(user_id)
        return ActivateResponse(message="Utilisateur activé", is_active=True)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


@router.post("/users/{user_id}/deactivate", response_model=ActivateResponse)
async def deactivate_user(
    user_id: UUID,
    admin_id: AdminUser,
    use_case: DeactivateUserUseCaseDep,
):
    """Deactivate a user account (admin only)."""
    try:
        await use_case.execute(user_id, admin_id)
        return ActivateResponse(message="Utilisateur désactivé", is_active=False)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    except CannotModifyOwnAccountError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    admin_id: AdminUser,
    use_case: DeleteUserUseCaseDep,
):
    """Delete a user account permanently (admin only)."""
    try:
        await use_case.execute(user_id, admin_id)
        return MessageResponse(message="Utilisateur supprimé")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    except CannotModifyOwnAccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Gemini Settings Endpoints
# =============================================================================


@router.get("/gemini/settings", response_model=GeminiSettingsResponse)
async def get_gemini_settings(
    admin_id: AdminUser,
    redis: RedisClient,
):
    """Get Gemini model settings (admin only)."""
    cache = CacheService(redis)
    current_model = await cache.get_gemini_model()

    return GeminiSettingsResponse(
        current_model=current_model,
        available_models=GeminiAnonymizer.AVAILABLE_MODELS,
        default_model=GeminiAnonymizer.DEFAULT_MODEL,
    )


@router.post("/gemini/settings", response_model=GeminiSettingsResponse)
async def set_gemini_model(
    request: GeminiSetModelRequest,
    admin_id: AdminUser,
    redis: RedisClient,
):
    """Set Gemini model (admin only)."""
    if request.model not in GeminiAnonymizer.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle invalide. Modèles disponibles: {', '.join(GeminiAnonymizer.AVAILABLE_MODELS)}",
        )

    cache = CacheService(redis)
    await cache.set_gemini_model(request.model)

    return GeminiSettingsResponse(
        current_model=request.model,
        available_models=GeminiAnonymizer.AVAILABLE_MODELS,
        default_model=GeminiAnonymizer.DEFAULT_MODEL,
    )


@router.post("/gemini/test", response_model=GeminiTestResponse)
async def test_gemini_model(
    request: GeminiSetModelRequest,
    admin_id: AdminUser,
    settings: AppSettings,
):
    """Test a Gemini model (admin only)."""
    anonymizer = GeminiAnonymizer(settings)
    result = await anonymizer.test_model(request.model)

    return GeminiTestResponse(
        success=result["success"],
        model=result["model"],
        response_time_ms=result["response_time_ms"],
        message=result["message"],
    )
