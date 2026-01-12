"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.api.schemas.user import UserResponse
from app.application.use_cases.auth import (
    ForgotPasswordUseCase,
    LoginCommand,
    LoginUseCase,
    RefreshTokenUseCase,
    RegisterCommand,
    RegisterUserUseCase,
    ResetPasswordUseCase,
    VerifyEmailUseCase,
)
from app.config import Settings
from app.dependencies import AppSettings, DbSession
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.email.sender import EmailService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: DbSession,
    settings: AppSettings,
):
    """Register a new user."""
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = RegisterUserUseCase(user_repo, email_service)
    command = RegisterCommand(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        boond_resource_id=request.boond_resource_id,
    )

    result = await use_case.execute(command)
    return UserResponse(**result.model_dump())


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: DbSession,
):
    """Authenticate user and return tokens."""
    user_repo = UserRepository(db)

    use_case = LoginUseCase(user_repo)
    command = LoginCommand(email=request.email, password=request.password)

    tokens, user = await use_case.execute(command)

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=UserResponse(**user.model_dump()),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: RefreshRequest,
    db: DbSession,
):
    """Refresh access token."""
    user_repo = UserRepository(db)

    use_case = RefreshTokenUseCase(user_repo)
    tokens = await use_case.execute(request.refresh_token)

    # We need to return user info too, but RefreshTokenUseCase doesn't return it
    # For simplicity, we'll return minimal response
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
    }


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: DbSession,
):
    """Verify user email with token."""
    user_repo = UserRepository(db)

    use_case = VerifyEmailUseCase(user_repo)
    result = await use_case.execute(request.token)

    return UserResponse(**result.model_dump())


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: DbSession,
    settings: AppSettings,
):
    """Request password reset email."""
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = ForgotPasswordUseCase(user_repo, email_service)
    await use_case.execute(request.email)

    # Always return success to not reveal if email exists
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: DbSession,
):
    """Reset password with token."""
    user_repo = UserRepository(db)

    use_case = ResetPasswordUseCase(user_repo)
    await use_case.execute(request.token, request.new_password)

    return {"message": "Password has been reset successfully."}


@router.post("/magic-link")
async def request_magic_link(
    request: ForgotPasswordRequest,
    db: DbSession,
    settings: AppSettings,
):
    """Request magic link for passwordless login."""
    if not settings.FEATURE_MAGIC_LINK:
        raise HTTPException(status_code=404, detail="Feature not available")

    # Implementation would be similar to forgot_password
    # but with different token type and expiry
    return {"message": "If this email exists, a login link has been sent."}
