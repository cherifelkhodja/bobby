"""Admin endpoints for system management."""

from datetime import UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select

from app.api.dependencies import AdminUser
from app.api.schemas.admin import (
    ActivateResponse,
    BoondResourceResponse,
    BoondResourcesListResponse,
    BoondStatusResponse,
    ChangeRoleRequest,
    CvAiSetProviderRequest,
    CvAiSettingsResponse,
    CvAiTestResponse,
    CvGeneratorBetaSetModelRequest,
    CvGeneratorBetaSettingsResponse,
    GeminiSetModelRequest,
    GeminiSettingsResponse,
    GeminiTestResponse,
    MessageResponse,
    InpiTestResponse,
    SireneTestResponse,
    SyncResponse,
    TestConnectionResponse,
    TurnoverITSkillResponse,
    TurnoverITSkillsResponse,
    TurnoverITSyncResponse,
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
from app.dependencies import AppSettings, AppSettingsSvc, DbSession
from app.infrastructure.anonymizer.gemini_anonymizer import GeminiAnonymizer
from app.infrastructure.anonymizer.job_posting_anonymizer import SKILLS_SYNC_INTERVAL
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.cache.redis import CacheService
from app.infrastructure.database.models import TurnoverITSkillModel, TurnoverITSkillsMetadataModel
from app.infrastructure.database.repositories import OpportunityRepository, UserRepository
from app.infrastructure.settings import (
    AVAILABLE_CLAUDE_MODELS,
    AVAILABLE_CV_AI_PROVIDERS,
    AVAILABLE_GEMINI_MODELS,
)
from app.infrastructure.turnoverit.client import TurnoverITClient
from app.contract_management.api.schemas import (
    ContractCompanyRequest,
    ContractCompanyResponse,
)
from app.contract_management.infrastructure.models import ContractCompanyModel

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
BoondResourcesUseCaseDep = Annotated[
    GetBoondResourcesUseCase, Depends(get_boond_resources_use_case)
]


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
    settings_svc: AppSettingsSvc,
):
    """Get Gemini model settings (admin only)."""
    current_model = await settings_svc.get_gemini_model()
    available_models = [m["id"] for m in AVAILABLE_GEMINI_MODELS]

    return GeminiSettingsResponse(
        current_model=current_model,
        available_models=available_models,
        default_model=GeminiAnonymizer.DEFAULT_MODEL,
    )


@router.post("/gemini/settings", response_model=GeminiSettingsResponse)
async def set_gemini_model(
    request: GeminiSetModelRequest,
    admin_id: AdminUser,
    settings_svc: AppSettingsSvc,
):
    """Set Gemini model (admin only)."""
    available_models = [m["id"] for m in AVAILABLE_GEMINI_MODELS]
    if request.model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle invalide. Modèles disponibles: {', '.join(available_models)}",
        )

    await settings_svc.set("gemini_model", request.model, admin_id)

    return GeminiSettingsResponse(
        current_model=request.model,
        available_models=available_models,
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


# =============================================================================
# CV AI Provider Settings Endpoints
# =============================================================================


@router.get("/cv-ai/settings", response_model=CvAiSettingsResponse)
async def get_cv_ai_settings(
    admin_id: AdminUser,
    settings_svc: AppSettingsSvc,
):
    """Get CV AI provider settings (admin only)."""
    current_provider = await settings_svc.get_cv_ai_provider()

    if current_provider == "claude":
        current_model = await settings_svc.get_cv_ai_model_claude()
    else:
        current_model = await settings_svc.get_gemini_model_cv()

    return CvAiSettingsResponse(
        current_provider=current_provider,
        current_model=current_model,
        available_providers=[{"id": p["id"], "name": p["name"]} for p in AVAILABLE_CV_AI_PROVIDERS],
        available_models_gemini=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_GEMINI_MODELS
        ],
        available_models_claude=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_CLAUDE_MODELS
        ],
    )


@router.post("/cv-ai/settings", response_model=CvAiSettingsResponse)
async def set_cv_ai_provider(
    request: CvAiSetProviderRequest,
    admin_id: AdminUser,
    settings_svc: AppSettingsSvc,
):
    """Set CV AI provider and model (admin only)."""
    # Validate provider
    valid_providers = [p["id"] for p in AVAILABLE_CV_AI_PROVIDERS]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provider invalide. Providers disponibles: {', '.join(valid_providers)}",
        )

    # Validate model for the selected provider
    if request.provider == "claude":
        valid_models = [m["id"] for m in AVAILABLE_CLAUDE_MODELS]
    else:
        valid_models = [m["id"] for m in AVAILABLE_GEMINI_MODELS]

    if request.model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle invalide pour {request.provider}. Modèles disponibles: {', '.join(valid_models)}",
        )

    # Save provider
    await settings_svc.set("cv_ai_provider", request.provider, admin_id)

    # Save model for the selected provider
    if request.provider == "claude":
        await settings_svc.set("cv_ai_model_claude", request.model, admin_id)
    else:
        await settings_svc.set("gemini_model_cv", request.model, admin_id)

    return CvAiSettingsResponse(
        current_provider=request.provider,
        current_model=request.model,
        available_providers=[{"id": p["id"], "name": p["name"]} for p in AVAILABLE_CV_AI_PROVIDERS],
        available_models_gemini=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_GEMINI_MODELS
        ],
        available_models_claude=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_CLAUDE_MODELS
        ],
    )


@router.post("/cv-ai/test", response_model=CvAiTestResponse)
async def test_cv_ai_provider(
    request: CvAiSetProviderRequest,
    admin_id: AdminUser,
    settings: AppSettings,
):
    """Test a CV AI provider/model (admin only)."""
    import time

    start = time.time()

    try:
        if request.provider == "claude":
            if not settings.ANTHROPIC_API_KEY:
                return CvAiTestResponse(
                    success=False,
                    provider=request.provider,
                    model=request.model,
                    response_time_ms=0,
                    message="ANTHROPIC_API_KEY non configurée",
                )

            from anthropic import Anthropic

            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=request.model,
                max_tokens=50,
                messages=[{"role": "user", "content": "Réponds uniquement 'OK'."}],
            )
            text = response.content[0].text if response.content else ""
            elapsed = int((time.time() - start) * 1000)

            return CvAiTestResponse(
                success=True,
                provider=request.provider,
                model=request.model,
                response_time_ms=elapsed,
                message=f"Claude fonctionne. Réponse: {text.strip()[:100]}",
            )

        else:
            if not settings.GEMINI_API_KEY:
                return CvAiTestResponse(
                    success=False,
                    provider=request.provider,
                    model=request.model,
                    response_time_ms=0,
                    message="GEMINI_API_KEY non configurée",
                )

            from google import genai

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = await client.aio.models.generate_content(
                model=request.model,
                contents="Réponds uniquement 'OK'.",
            )
            text = response.text if response.text else ""
            elapsed = int((time.time() - start) * 1000)

            return CvAiTestResponse(
                success=True,
                provider=request.provider,
                model=request.model,
                response_time_ms=elapsed,
                message=f"Gemini fonctionne. Réponse: {text.strip()[:100]}",
            )

    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return CvAiTestResponse(
            success=False,
            provider=request.provider,
            model=request.model,
            response_time_ms=elapsed,
            message=f"Erreur: {str(e)[:200]}",
        )


# =============================================================================
# CV Generator Beta Settings Endpoints
# =============================================================================


@router.get("/cv-generator-beta/settings", response_model=CvGeneratorBetaSettingsResponse)
async def get_cv_generator_beta_settings(
    admin_id: AdminUser,
    settings_svc: AppSettingsSvc,
):
    """Get CV Generator Beta model settings (admin only)."""
    current_model = await settings_svc.get_cv_generator_beta_model()

    return CvGeneratorBetaSettingsResponse(
        current_model=current_model,
        available_models=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_CLAUDE_MODELS
        ],
    )


@router.post("/cv-generator-beta/settings", response_model=CvGeneratorBetaSettingsResponse)
async def set_cv_generator_beta_settings(
    request: CvGeneratorBetaSetModelRequest,
    admin_id: AdminUser,
    settings_svc: AppSettingsSvc,
):
    """Set CV Generator Beta Claude model (admin only)."""
    valid_models = [m["id"] for m in AVAILABLE_CLAUDE_MODELS]

    if request.model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Modèle invalide. Modèles disponibles: {', '.join(valid_models)}",
        )

    await settings_svc.set("cv_generator_beta_model", request.model, admin_id)

    return CvGeneratorBetaSettingsResponse(
        current_model=request.model,
        available_models=[
            {"id": m["id"], "name": m["name"], "description": m.get("description", "")}
            for m in AVAILABLE_CLAUDE_MODELS
        ],
    )


@router.post("/cv-generator-beta/test", response_model=CvAiTestResponse)
async def test_cv_generator_beta(
    request: CvGeneratorBetaSetModelRequest,
    admin_id: AdminUser,
    settings: AppSettings,
):
    """Test CV Generator Beta Claude model (admin only)."""
    import time

    start = time.time()

    if not settings.ANTHROPIC_API_KEY:
        return CvAiTestResponse(
            success=False,
            provider="claude",
            model=request.model,
            response_time_ms=0,
            message="ANTHROPIC_API_KEY non configurée",
        )

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=request.model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Réponds uniquement 'OK'."}],
        )
        text = response.content[0].text if response.content else ""
        elapsed = int((time.time() - start) * 1000)

        return CvAiTestResponse(
            success=True,
            provider="claude",
            model=request.model,
            response_time_ms=elapsed,
            message=f"Claude fonctionne. Réponse: {text.strip()[:100]}",
        )

    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return CvAiTestResponse(
            success=False,
            provider="claude",
            model=request.model,
            response_time_ms=elapsed,
            message=f"Erreur: {str(e)[:200]}",
        )


# =============================================================================
# Turnover-IT Skills Endpoints
# =============================================================================


@router.get("/turnoverit/skills", response_model=TurnoverITSkillsResponse)
async def get_turnoverit_skills(
    admin_id: AdminUser,
    db: DbSession,
    search: str = Query(None, description="Search skills by name"),
):
    """Get cached Turnover-IT skills (admin only).

    Returns the list of skills cached from Turnover-IT API.
    Skills are synced automatically every 30 days.
    """
    try:
        # Get metadata
        result = await db.execute(
            select(TurnoverITSkillsMetadataModel).where(TurnoverITSkillsMetadataModel.id == 1)
        )
        metadata = result.scalar_one_or_none()

        # Get skills
        query = select(TurnoverITSkillModel).order_by(TurnoverITSkillModel.name)
        if search:
            query = query.where(TurnoverITSkillModel.name.ilike(f"%{search}%"))

        result = await db.execute(query)
        skills = result.scalars().all()

        return TurnoverITSkillsResponse(
            skills=[TurnoverITSkillResponse(name=s.name, slug=s.slug) for s in skills],
            total=len(skills),
            last_synced_at=metadata.last_synced_at if metadata else None,
            sync_interval_days=SKILLS_SYNC_INTERVAL.days,
        )
    except Exception:
        # Table might not exist yet
        return TurnoverITSkillsResponse(
            skills=[],
            total=0,
            last_synced_at=None,
            sync_interval_days=SKILLS_SYNC_INTERVAL.days,
        )


@router.post("/turnoverit/skills/sync", response_model=TurnoverITSyncResponse)
async def sync_turnoverit_skills(
    admin_id: AdminUser,
    db: DbSession,
    settings: AppSettings,
):
    """Force sync Turnover-IT skills from API (admin only).

    Fetches all skills from Turnover-IT API and stores them in the database.
    This is normally done automatically every 30 days.
    """
    client = TurnoverITClient(settings)

    try:
        # Fetch all skills from API
        skills = await client.fetch_all_skills()

        if not skills:
            return TurnoverITSyncResponse(
                success=False,
                synced_count=0,
                message="Aucun skill récupéré depuis Turnover-IT. Vérifiez la clé API.",
            )

        # Clear existing skills
        await db.execute(delete(TurnoverITSkillModel))

        # Insert new skills
        from datetime import datetime

        for skill in skills:
            skill_model = TurnoverITSkillModel(
                name=skill["name"],
                slug=skill["slug"],
            )
            db.add(skill_model)

        # Update metadata
        result = await db.execute(
            select(TurnoverITSkillsMetadataModel).where(TurnoverITSkillsMetadataModel.id == 1)
        )
        metadata = result.scalar_one_or_none()

        if metadata:
            metadata.last_synced_at = datetime.now(UTC)
            metadata.total_skills = len(skills)
        else:
            metadata = TurnoverITSkillsMetadataModel(
                id=1,
                last_synced_at=datetime.now(UTC),
                total_skills=len(skills),
            )
            db.add(metadata)

        await db.commit()

        return TurnoverITSyncResponse(
            success=True,
            synced_count=len(skills),
            message=f"{len(skills)} skills synchronisés depuis Turnover-IT",
        )

    except Exception as e:
        await db.rollback()
        return TurnoverITSyncResponse(
            success=False,
            synced_count=0,
            message=f"Erreur lors de la synchronisation: {str(e)}",
        )


# =============================================================================
# INSEE Sirene Endpoints
# =============================================================================


@router.post("/sirene/test", response_model=SireneTestResponse)
async def test_sirene_connection(
    admin_id: AdminUser,
    settings: AppSettings,
):
    """Test INSEE Sirene API connection (admin only).

    Uses a well-known SIRET to verify the API key is working.
    """
    import time

    import httpx

    configured = bool(settings.SIRENE_API_KEY)

    if not configured:
        return SireneTestResponse(
            success=False,
            configured=False,
            response_time_ms=0,
            message="SIRENE_API_KEY non configurée",
        )

    # Use a dummy SIRET — 404 (not found) still proves the key is valid and the API reachable
    test_siret = "00000000000000"
    url = f"{settings.SIRENE_API_URL}/siret/{test_siret}"
    headers = {
        "X-INSEE-Api-Key-Integration": settings.SIRENE_API_KEY,
        "Accept": "application/json",
    }

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
        elapsed = int((time.time() - start) * 1000)

        if resp.status_code in (200, 404):
            # 200 = found, 404 = not found — both mean the API is reachable and the key is valid
            return SireneTestResponse(
                success=True,
                configured=True,
                response_time_ms=elapsed,
                message=f"INSEE Sirene fonctionne ({elapsed}ms)",
            )
        elif resp.status_code in (401, 403):
            return SireneTestResponse(
                success=False,
                configured=True,
                response_time_ms=elapsed,
                message="Clé API INSEE invalide ou accès refusé",
            )
        else:
            return SireneTestResponse(
                success=False,
                configured=True,
                response_time_ms=elapsed,
                message=f"Erreur INSEE: HTTP {resp.status_code}",
            )

    except httpx.TimeoutException:
        elapsed = int((time.time() - start) * 1000)
        return SireneTestResponse(
            success=False,
            configured=True,
            response_time_ms=elapsed,
            message="Timeout: l'API INSEE n'a pas répondu",
        )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return SireneTestResponse(
            success=False,
            configured=True,
            response_time_ms=elapsed,
            message=f"Erreur: {str(e)[:200]}",
        )


# =============================================================================
# INPI RNE Endpoints
# =============================================================================


@router.post("/inpi/test", response_model=InpiTestResponse)
async def test_inpi_connection(
    admin_id: AdminUser,
    settings: AppSettings,
):
    """Test INPI RNE API connection (admin only).

    Utilise INPI_USERNAME/INPI_PASSWORD pour auto-login (JWT rafraîchi automatiquement).
    Fallback sur INPI_TOKEN statique si les credentials ne sont pas configurés.
    """
    import time

    from app.third_party.infrastructure.adapters.inpi_client import InpiClient

    configured = bool(settings.INPI_USERNAME and settings.INPI_PASSWORD) or bool(settings.INPI_TOKEN)

    if not configured:
        return InpiTestResponse(
            success=False,
            configured=False,
            response_time_ms=0,
            message="INPI non configuré — ajouter INPI_USERNAME + INPI_PASSWORD dans AWS Secrets Manager",
        )

    inpi_client = InpiClient(
        username=settings.INPI_USERNAME,
        password=settings.INPI_PASSWORD,
        token=settings.INPI_TOKEN,
    )

    # Test with GEMINI's own SIREN (real payload verified)
    test_siren = "842799959"
    start = time.time()
    try:
        result = await inpi_client.get_company(test_siren)
        elapsed = int((time.time() - start) * 1000)

        if result is not None:
            details = []
            if result.legal_form_label:
                details.append(f"Forme: {result.legal_form_label}")
            if result.capital_amount is not None:
                details.append(f"Capital: {result.capital_amount:,.0f} {result.capital_currency or 'EUR'}")
            if result.greffe_city:
                details.append(f"Greffe: {result.greffe_city}")
            detail_str = " | ".join(details) if details else "données récupérées"
            return InpiTestResponse(
                success=True,
                configured=True,
                response_time_ms=elapsed,
                message=f"INPI RNE fonctionne ({elapsed}ms) — {result.company_name} — {detail_str}",
            )
        else:
            # result is None : soit SIREN non trouvé, soit token non obtenu
            from app.third_party.infrastructure.adapters.inpi_client import _get_inpi_token
            token_check = await _get_inpi_token(
                settings.INPI_USERNAME, settings.INPI_PASSWORD, settings.INPI_TOKEN
            )
            if not token_check:
                return InpiTestResponse(
                    success=False,
                    configured=False,
                    response_time_ms=elapsed,
                    message="INPI : authentification échouée — vérifier INPI_USERNAME/INPI_PASSWORD dans AWS Secrets",
                )
            return InpiTestResponse(
                success=True,
                configured=True,
                response_time_ms=elapsed,
                message=f"INPI RNE accessible ({elapsed}ms) — authentification OK",
            )

    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return InpiTestResponse(
            success=False,
            configured=True,
            response_time_ms=elapsed,
            message=f"Erreur: {str(e)[:200]}",
        )


# ─── Contract Article Templates ───────────────────────────────────────────────

from pydantic import BaseModel as _PydanticBase
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from app.dependencies import get_db as _get_db


class ArticleTemplateResponse(_PydanticBase):
    article_key: str
    article_number: int
    title: str
    content: str
    is_editable: bool
    is_active: bool
    is_optional: bool


class ArticleTemplateCreateRequest(_PydanticBase):
    article_key: str
    title: str
    content: str = ""
    is_editable: bool = True
    is_active: bool = True
    is_optional: bool = False


class ArticleTemplateUpdateRequest(_PydanticBase):
    content: str | None = None
    title: str | None = None
    is_editable: bool | None = None
    is_active: bool | None = None
    is_optional: bool | None = None


class ArticleReorderRequest(_PydanticBase):
    ordered_keys: list[str]


@router.post(
    "/contract-articles",
    response_model=ArticleTemplateResponse,
    status_code=201,
    summary="Create a contract article template",
)
async def create_contract_article(
    body: ArticleTemplateCreateRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Create a new contract article template. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    repo = ArticleTemplateRepository(db)
    existing = await repo.get_by_key(body.article_key)
    if existing:
        raise HTTPException(status_code=409, detail=f"La clé '{body.article_key}' est déjà utilisée")
    created = await repo.create(
        article_key=body.article_key,
        title=body.title,
        content=body.content,
        is_editable=body.is_editable,
        is_active=body.is_active,
        is_optional=body.is_optional,
        created_by=admin_id,
    )
    await db.commit()
    return ArticleTemplateResponse(
        article_key=created.article_key,
        article_number=created.article_number,
        title=created.title,
        content=created.content,
        is_editable=created.is_editable,
        is_active=created.is_active,
        is_optional=created.is_optional,
    )


@router.get(
    "/contract-articles",
    response_model=list[ArticleTemplateResponse],
    summary="List all contract article templates",
)
async def list_contract_articles(
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """List all contract article templates ordered by article number. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    articles = await ArticleTemplateRepository(db).get_all()
    return [
        ArticleTemplateResponse(
            article_key=a.article_key,
            article_number=a.article_number,
            title=a.title,
            content=a.content,
            is_editable=a.is_editable,
            is_active=a.is_active,
            is_optional=a.is_optional,
        )
        for a in articles
    ]


@router.post(
    "/contract-articles/reorder",
    status_code=204,
    summary="Reorder contract article templates",
)
async def reorder_contract_articles(
    body: ArticleReorderRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Update article_number for all articles according to the provided order. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    await ArticleTemplateRepository(db).reorder(body.ordered_keys)
    await db.commit()


@router.delete(
    "/contract-articles/{article_key}",
    status_code=204,
    summary="Delete a contract article template",
)
async def delete_contract_article(
    article_key: str,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Permanently delete a contract article template. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    deleted = await ArticleTemplateRepository(db).delete(article_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Article '{article_key}' introuvable")
    await db.commit()


@router.patch(
    "/contract-articles/{article_key}",
    response_model=ArticleTemplateResponse,
    summary="Update a contract article template",
)
async def update_contract_article(
    article_key: str,
    body: ArticleTemplateUpdateRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Update content, title, is_editable or is_active of a contract article. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_article_template_repo import (
        ArticleTemplateRepository,
    )
    updated = await ArticleTemplateRepository(db).update(
        article_key,
        content=body.content,
        title=body.title,
        is_editable=body.is_editable,
        is_active=body.is_active,
        is_optional=body.is_optional,
        updated_by=admin_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Article '{article_key}' introuvable")
    return ArticleTemplateResponse(
        article_key=updated.article_key,
        article_number=updated.article_number,
        title=updated.title,
        content=updated.content,
        is_editable=updated.is_editable,
        is_active=updated.is_active,
        is_optional=updated.is_optional,
    )


# ─── Contract Annex Templates ─────────────────────────────────────────────────


class AnnexTemplateResponse(_PydanticBase):
    annexe_key: str
    annexe_number: int
    title: str
    content: str
    is_conditional: bool
    condition_field: str | None
    is_active: bool


class AnnexTemplateCreateRequest(_PydanticBase):
    annexe_key: str
    title: str
    content: str = ""
    is_active: bool = True


class AnnexTemplateUpdateRequest(_PydanticBase):
    content: str | None = None
    title: str | None = None
    is_active: bool | None = None


@router.post(
    "/contract-annexes",
    response_model=AnnexTemplateResponse,
    status_code=201,
    summary="Create a contract annex template",
)
async def create_contract_annex(
    body: AnnexTemplateCreateRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Create a new contract annex template. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    repo = AnnexTemplateRepository(db)
    existing = await repo.get_by_key(body.annexe_key)
    if existing:
        raise HTTPException(status_code=409, detail=f"La clé '{body.annexe_key}' est déjà utilisée")
    created = await repo.create(
        annexe_key=body.annexe_key,
        title=body.title,
        content=body.content,
        is_active=body.is_active,
        created_by=admin_id,
    )
    await db.commit()
    return AnnexTemplateResponse(
        annexe_key=created.annexe_key,
        annexe_number=created.annexe_number,
        title=created.title,
        content=created.content,
        is_conditional=created.is_conditional,
        condition_field=created.condition_field,
        is_active=created.is_active,
    )


@router.get(
    "/contract-annexes",
    response_model=list[AnnexTemplateResponse],
    summary="List all contract annex templates",
)
async def list_contract_annexes(
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """List all contract annex templates ordered by annexe number. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    annexes = await AnnexTemplateRepository(db).get_all()
    return [
        AnnexTemplateResponse(
            annexe_key=a.annexe_key,
            annexe_number=a.annexe_number,
            title=a.title,
            content=a.content,
            is_conditional=a.is_conditional,
            condition_field=a.condition_field,
            is_active=a.is_active,
        )
        for a in annexes
    ]


@router.post(
    "/contract-annexes/reorder",
    status_code=204,
    summary="Reorder contract annex templates",
)
async def reorder_contract_annexes(
    body: ArticleReorderRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Update annexe_number for all annexes according to the provided order. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    await AnnexTemplateRepository(db).reorder(body.ordered_keys)
    await db.commit()


@router.delete(
    "/contract-annexes/{annexe_key}",
    status_code=204,
    summary="Delete a contract annex template",
)
async def delete_contract_annex(
    annexe_key: str,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Permanently delete a contract annex template. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    deleted = await AnnexTemplateRepository(db).delete(annexe_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Annexe '{annexe_key}' introuvable")
    await db.commit()


@router.patch(
    "/contract-annexes/{annexe_key}",
    response_model=AnnexTemplateResponse,
    summary="Update a contract annex template",
)
async def update_contract_annex(
    annexe_key: str,
    body: AnnexTemplateUpdateRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Update content, title or is_active of a contract annex. Admin only."""
    from app.contract_management.infrastructure.adapters.postgres_annex_template_repo import (
        AnnexTemplateRepository,
    )
    updated = await AnnexTemplateRepository(db).update(
        annexe_key,
        content=body.content,
        title=body.title,
        is_active=body.is_active,
        updated_by=admin_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Annexe '{annexe_key}' introuvable")
    await db.commit()
    return AnnexTemplateResponse(
        annexe_key=updated.annexe_key,
        annexe_number=updated.annexe_number,
        title=updated.title,
        content=updated.content,
        is_conditional=updated.is_conditional,
        condition_field=updated.condition_field,
        is_active=updated.is_active,
    )


# ── Contract companies (sociétés émettrices) ──────────────────────────────────

def _company_to_response(m: ContractCompanyModel) -> ContractCompanyResponse:
    return ContractCompanyResponse(
        id=m.id,
        name=m.name,
        legal_form=m.legal_form,
        capital=m.capital,
        head_office=m.head_office,
        rcs_city=m.rcs_city,
        rcs_number=m.rcs_number,
        representative_is_entity=m.representative_is_entity,
        representative_name=m.representative_name,
        representative_quality=m.representative_quality,
        representative_sub_name=m.representative_sub_name,
        representative_sub_quality=m.representative_sub_quality,
        signatory_name=m.signatory_name,
        invoices_company_mail=m.invoices_company_mail,
        color_code=m.color_code,
        has_logo=bool(m.logo_s3_key),
        is_default=m.is_default,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.get(
    "/contract-companies",
    response_model=list[ContractCompanyResponse],
    summary="List issuing companies",
)
async def list_contract_companies(
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """List all contract issuing companies. Admin only."""
    from sqlalchemy import select as _select
    result = await db.execute(_select(ContractCompanyModel).order_by(ContractCompanyModel.created_at))
    return [_company_to_response(m) for m in result.scalars().all()]


@router.post(
    "/contract-companies",
    response_model=ContractCompanyResponse,
    status_code=201,
    summary="Create issuing company",
)
async def create_contract_company(
    body: ContractCompanyRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Create a new contract issuing company. Admin only."""
    from uuid import uuid4 as _uuid4
    from datetime import datetime as _dt
    # If this one is set as default, unset the others
    if body.is_default:
        await db.execute(
            ContractCompanyModel.__table__.update().values(is_default=False)
        )
    m = ContractCompanyModel(
        id=_uuid4(),
        name=body.name,
        legal_form=body.legal_form,
        capital=body.capital,
        head_office=body.head_office,
        rcs_city=body.rcs_city,
        rcs_number=body.rcs_number,
        representative_is_entity=body.representative_is_entity,
        representative_name=body.representative_name,
        representative_quality=body.representative_quality,
        representative_sub_name=body.representative_sub_name,
        representative_sub_quality=body.representative_sub_quality,
        signatory_name=body.signatory_name,
        invoices_company_mail=body.invoices_company_mail,
        color_code=body.color_code,
        is_default=body.is_default,
        is_active=body.is_active,
        created_at=_dt.utcnow(),
        updated_at=_dt.utcnow(),
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _company_to_response(m)


@router.patch(
    "/contract-companies/{company_id}",
    response_model=ContractCompanyResponse,
    summary="Update issuing company",
)
async def update_contract_company(
    company_id: UUID,
    body: ContractCompanyRequest,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Update an issuing company. Admin only."""
    from sqlalchemy import select as _select
    from datetime import datetime as _dt
    result = await db.execute(_select(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Société introuvable")
    if body.is_default and not m.is_default:
        await db.execute(
            ContractCompanyModel.__table__.update().values(is_default=False)
        )
    m.name = body.name
    m.legal_form = body.legal_form
    m.capital = body.capital
    m.head_office = body.head_office
    m.rcs_city = body.rcs_city
    m.rcs_number = body.rcs_number
    m.representative_is_entity = body.representative_is_entity
    m.representative_name = body.representative_name
    m.representative_quality = body.representative_quality
    m.representative_sub_name = body.representative_sub_name
    m.representative_sub_quality = body.representative_sub_quality
    m.signatory_name = body.signatory_name
    m.invoices_company_mail = body.invoices_company_mail
    m.color_code = body.color_code
    m.is_default = body.is_default
    m.is_active = body.is_active
    m.updated_at = _dt.utcnow()
    await db.commit()
    await db.refresh(m)
    return _company_to_response(m)


@router.delete(
    "/contract-companies/{company_id}",
    status_code=204,
    summary="Delete issuing company",
)
async def delete_contract_company(
    company_id: UUID,
    admin_id: AdminUser,
    db: _AsyncSession = Depends(_get_db),
):
    """Delete an issuing company. Admin only."""
    from sqlalchemy import select as _select, delete as _delete
    result = await db.execute(_select(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Société introuvable")
    await db.execute(_delete(ContractCompanyModel).where(ContractCompanyModel.id == company_id))
    await db.commit()


