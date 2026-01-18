"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.rate_limiter import (
    limiter,
    rate_limit_forgot_password,
    rate_limit_login,
    rate_limit_register,
)
from app.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
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
from app.infrastructure.audit import audit_logger, AuditAction, AuditResource
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.email.sender import EmailService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("3/minute")
async def register(
    request: RegisterRequest,
    http_request: Request,
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

    # Audit log
    audit_logger.log(
        AuditAction.USER_CREATE,
        AuditResource.USER,
        user_id=result.id,
        ip_address=http_request.client.host if http_request.client else None,
        details={"email": result.email},
    )

    return UserResponse(**result.model_dump())


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: LoginRequest,
    http_request: Request,
    db: DbSession,
):
    """Authenticate user and return tokens."""
    user_repo = UserRepository(db)
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("User-Agent")

    use_case = LoginUseCase(user_repo)
    command = LoginCommand(email=request.email, password=request.password)

    try:
        tokens, user = await use_case.execute(command)

        # Audit successful login
        audit_logger.log_login_success(
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            user=UserResponse(**user.model_dump()),
        )
    except HTTPException as e:
        # Audit failed login
        audit_logger.log_login_failure(
            email=request.email,
            reason=str(e.detail),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    db: DbSession,
):
    """Refresh access token."""
    user_repo = UserRepository(db)

    use_case = RefreshTokenUseCase(user_repo)
    tokens = await use_case.execute(request.refresh_token)

    return RefreshResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )


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
@limiter.limit("3/minute")
async def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    db: DbSession,
    settings: AppSettings,
):
    """Request password reset email."""
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = ForgotPasswordUseCase(user_repo, email_service)
    await use_case.execute(request.email)

    # Audit log (always log, even if email doesn't exist - for security monitoring)
    audit_logger.log(
        AuditAction.PASSWORD_RESET_REQUEST,
        AuditResource.USER,
        ip_address=http_request.client.host if http_request.client else None,
        details={"email": request.email},
    )

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
