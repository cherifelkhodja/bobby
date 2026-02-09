"""Invitation management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.schemas.user import UserResponse
from app.application.use_cases.invitations import (
    AcceptInvitationCommand,
    AcceptInvitationUseCase,
    CreateInvitationCommand,
    CreateInvitationUseCase,
    DeleteInvitationUseCase,
    InvitationAlreadyAcceptedError,
    InvitationAlreadyExistsError,
    InvitationExpiredError,
    InvitationNotFoundError,
    ListPendingInvitationsUseCase,
    ResendInvitationUseCase,
    UserAlreadyExistsError,
    ValidateInvitationUseCase,
)
from app.dependencies import AppSettings, DbSession
from app.infrastructure.database.repositories import InvitationRepository, UserRepository
from app.infrastructure.email.sender import EmailService
from app.infrastructure.security.jwt import decode_token

router = APIRouter()


# Request/Response schemas
class CreateInvitationRequest(BaseModel):
    """Request to create an invitation."""

    email: EmailStr
    role: str  # user, commercial, rh, admin
    boond_resource_id: str | None = None
    manager_boond_id: str | None = None
    phone: str | None = None  # International format +33...
    first_name: str | None = None  # Pre-filled from BoondManager
    last_name: str | None = None  # Pre-filled from BoondManager


class InvitationResponse(BaseModel):
    """Invitation response."""

    id: UUID
    email: str
    role: str
    phone: str | None = None
    invited_by: UUID
    expires_at: str
    is_expired: bool
    is_accepted: bool
    created_at: str


class InvitationValidationResponse(BaseModel):
    """Response for invitation validation."""

    email: str
    role: str
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_valid: bool
    hours_until_expiry: int


class AcceptInvitationRequest(BaseModel):
    """Request to accept an invitation."""

    token: str
    first_name: str
    last_name: str
    password: str
    phone: str | None = None


class InvitationsListResponse(BaseModel):
    """List of invitations response."""

    invitations: list[InvitationResponse]
    total: int


async def require_admin(db: DbSession, authorization: str) -> UUID:
    """Verify user is admin and return user ID."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié")

    token = authorization[7:]
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload.sub)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Accès administrateur requis")

    return user_id


@router.post("", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    request: CreateInvitationRequest,
    db: DbSession,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Create a new invitation (admin only)."""
    admin_id = await require_admin(db, authorization)

    # Validate role
    if request.role not in ("user", "commercial", "rh", "admin"):
        raise HTTPException(status_code=400, detail="Rôle invalide")

    invitation_repo = InvitationRepository(db)
    user_repo = UserRepository(db)
    email_service = EmailService(settings)

    use_case = CreateInvitationUseCase(invitation_repo, user_repo, email_service)

    try:
        invitation = await use_case.execute(
            CreateInvitationCommand(
                email=request.email,
                role=request.role,
                invited_by=admin_id,
                boond_resource_id=request.boond_resource_id,
                manager_boond_id=request.manager_boond_id,
                phone=request.phone,
                first_name=request.first_name,
                last_name=request.last_name,
            )
        )

        return InvitationResponse(
            id=invitation.id,
            email=str(invitation.email),
            role=str(invitation.role),
            phone=invitation.phone,
            invited_by=invitation.invited_by,
            expires_at=invitation.expires_at.isoformat(),
            is_expired=invitation.is_expired,
            is_accepted=invitation.is_accepted,
            created_at=invitation.created_at.isoformat(),
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvitationAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=InvitationsListResponse)
async def list_invitations(
    db: DbSession,
    authorization: str = Header(default=""),
    skip: int = 0,
    limit: int = 50,
):
    """List all pending invitations (admin only)."""
    await require_admin(db, authorization)

    invitation_repo = InvitationRepository(db)

    use_case = ListPendingInvitationsUseCase(invitation_repo)
    invitations = await use_case.execute(skip=skip, limit=limit)
    total = await invitation_repo.count_pending()

    return InvitationsListResponse(
        invitations=[
            InvitationResponse(
                id=inv.id,
                email=str(inv.email),
                role=str(inv.role),
                phone=inv.phone,
                invited_by=inv.invited_by,
                expires_at=inv.expires_at.isoformat(),
                is_expired=inv.is_expired,
                is_accepted=inv.is_accepted,
                created_at=inv.created_at.isoformat(),
            )
            for inv in invitations
        ],
        total=total,
    )


@router.get("/validate/{token}", response_model=InvitationValidationResponse)
async def validate_invitation(
    token: str,
    db: DbSession,
):
    """Validate an invitation token (public endpoint)."""
    invitation_repo = InvitationRepository(db)

    use_case = ValidateInvitationUseCase(invitation_repo)

    try:
        invitation = await use_case.execute(token)
        return InvitationValidationResponse(
            email=str(invitation.email),
            role=str(invitation.role),
            phone=invitation.phone,
            first_name=invitation.first_name,
            last_name=invitation.last_name,
            is_valid=invitation.is_valid,
            hours_until_expiry=invitation.hours_until_expiry,
        )
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")
    except InvitationExpiredError:
        raise HTTPException(status_code=410, detail="Cette invitation a expiré")
    except InvitationAlreadyAcceptedError:
        raise HTTPException(status_code=410, detail="Cette invitation a déjà été acceptée")


@router.post("/accept", response_model=UserResponse)
async def accept_invitation(
    request: AcceptInvitationRequest,
    db: DbSession,
):
    """Accept an invitation and create user account (public endpoint)."""
    invitation_repo = InvitationRepository(db)
    user_repo = UserRepository(db)

    use_case = AcceptInvitationUseCase(invitation_repo, user_repo)

    try:
        user = await use_case.execute(
            AcceptInvitationCommand(
                token=request.token,
                first_name=request.first_name,
                last_name=request.last_name,
                password=request.password,
                phone=request.phone,
            )
        )

        return UserResponse(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=str(user.role),
            phone=user.phone,
            is_verified=user.is_verified,
            is_active=user.is_active,
            boond_resource_id=user.boond_resource_id,
            manager_boond_id=user.manager_boond_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")
    except InvitationExpiredError:
        raise HTTPException(status_code=410, detail="Cette invitation a expiré")
    except InvitationAlreadyAcceptedError:
        raise HTTPException(status_code=410, detail="Cette invitation a déjà été acceptée")
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    invitation_id: UUID,
    db: DbSession,
    settings: AppSettings,
    authorization: str = Header(default=""),
):
    """Resend an invitation email (admin only)."""
    await require_admin(db, authorization)

    invitation_repo = InvitationRepository(db)
    email_service = EmailService(settings)

    use_case = ResendInvitationUseCase(invitation_repo, email_service)

    try:
        invitation = await use_case.execute(invitation_id)

        return InvitationResponse(
            id=invitation.id,
            email=str(invitation.email),
            role=str(invitation.role),
            phone=invitation.phone,
            invited_by=invitation.invited_by,
            expires_at=invitation.expires_at.isoformat(),
            is_expired=invitation.is_expired,
            is_accepted=invitation.is_accepted,
            created_at=invitation.created_at.isoformat(),
        )
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")
    except InvitationAlreadyAcceptedError:
        raise HTTPException(status_code=410, detail="Cette invitation a déjà été acceptée")


@router.delete("/{invitation_id}", status_code=204)
async def delete_invitation(
    invitation_id: UUID,
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Delete/cancel an invitation (admin only)."""
    await require_admin(db, authorization)

    invitation_repo = InvitationRepository(db)

    use_case = DeleteInvitationUseCase(invitation_repo)

    try:
        await use_case.execute(invitation_id)
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")
    except InvitationAlreadyAcceptedError:
        raise HTTPException(status_code=410, detail="Cette invitation a déjà été acceptée")
