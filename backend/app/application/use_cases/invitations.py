"""Invitation use cases."""

import secrets
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Invitation, User
from app.domain.exceptions import DomainError
from app.domain.ports.repositories import InvitationRepositoryPort, UserRepositoryPort
from app.domain.ports.services import EmailServicePort
from app.domain.value_objects import Email, UserRole


class InvitationAlreadyExistsError(DomainError):
    """Raised when an invitation already exists for this email."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Une invitation est déjà en attente pour {email}")


class InvitationNotFoundError(DomainError):
    """Raised when invitation is not found."""

    def __init__(self) -> None:
        super().__init__("Invitation non trouvée")


class InvitationExpiredError(DomainError):
    """Raised when invitation has expired."""

    def __init__(self) -> None:
        super().__init__("Cette invitation a expiré")


class InvitationAlreadyAcceptedError(DomainError):
    """Raised when invitation was already accepted."""

    def __init__(self) -> None:
        super().__init__("Cette invitation a déjà été acceptée")


class UserAlreadyExistsError(DomainError):
    """Raised when user already exists with this email."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Un utilisateur existe déjà avec l'email {email}")


@dataclass
class CreateInvitationCommand:
    """Command to create an invitation."""

    email: str
    role: str
    invited_by: UUID
    boond_resource_id: str | None = None
    manager_boond_id: str | None = None
    phone: str | None = None


class CreateInvitationUseCase:
    """Use case to create a new invitation."""

    def __init__(
        self,
        invitation_repository: InvitationRepositoryPort,
        user_repository: UserRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self.invitation_repository = invitation_repository
        self.user_repository = user_repository
        self.email_service = email_service

    async def execute(self, command: CreateInvitationCommand) -> Invitation:
        """Create an invitation and send email."""
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(command.email)
        if existing_user:
            raise UserAlreadyExistsError(command.email)

        # Check if pending invitation already exists
        existing_invitation = await self.invitation_repository.get_by_email(command.email)
        if existing_invitation:
            raise InvitationAlreadyExistsError(command.email)

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Create invitation
        invitation = Invitation.create(
            email=Email(command.email),
            role=UserRole(command.role),
            invited_by=command.invited_by,
            token=token,
            validity_hours=48,
            boond_resource_id=command.boond_resource_id,
            manager_boond_id=command.manager_boond_id,
            phone=command.phone,
        )

        # Save invitation
        saved_invitation = await self.invitation_repository.save(invitation)

        # Send invitation email
        await self.email_service.send_invitation_email(
            to_email=command.email,
            token=token,
            role=command.role,
        )

        return saved_invitation


class ValidateInvitationUseCase:
    """Use case to validate an invitation token."""

    def __init__(self, invitation_repository: InvitationRepositoryPort) -> None:
        self.invitation_repository = invitation_repository

    async def execute(self, token: str) -> Invitation:
        """Validate invitation token and return invitation details."""
        invitation = await self.invitation_repository.get_by_token(token)

        if not invitation:
            raise InvitationNotFoundError()

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError()

        if invitation.is_expired:
            raise InvitationExpiredError()

        return invitation


@dataclass
class AcceptInvitationCommand:
    """Command to accept an invitation."""

    token: str
    first_name: str
    last_name: str
    password: str


class AcceptInvitationUseCase:
    """Use case to accept an invitation and create user."""

    def __init__(
        self,
        invitation_repository: InvitationRepositoryPort,
        user_repository: UserRepositoryPort,
    ) -> None:
        self.invitation_repository = invitation_repository
        self.user_repository = user_repository

    async def execute(self, command: AcceptInvitationCommand) -> User:
        """Accept invitation and create user account."""
        from app.infrastructure.security.password import hash_password

        # Get and validate invitation
        invitation = await self.invitation_repository.get_by_token(command.token)

        if not invitation:
            raise InvitationNotFoundError()

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError()

        if invitation.is_expired:
            raise InvitationExpiredError()

        # Check if user was created by another process
        existing_user = await self.user_repository.get_by_email(str(invitation.email))
        if existing_user:
            raise UserAlreadyExistsError(str(invitation.email))

        # Create user
        user = User(
            email=invitation.email,
            first_name=command.first_name,
            last_name=command.last_name,
            password_hash=hash_password(command.password),
            role=invitation.role,
            is_verified=True,  # Auto-verify since they came via invitation
            is_active=True,
            boond_resource_id=invitation.boond_resource_id,
            manager_boond_id=invitation.manager_boond_id,
            phone=invitation.phone,
        )

        saved_user = await self.user_repository.save(user)

        # Mark invitation as accepted
        invitation.accept()
        await self.invitation_repository.save(invitation)

        return saved_user


class DeleteInvitationUseCase:
    """Use case to delete/cancel an invitation."""

    def __init__(self, invitation_repository: InvitationRepositoryPort) -> None:
        self.invitation_repository = invitation_repository

    async def execute(self, invitation_id: UUID) -> bool:
        """Delete an invitation."""
        invitation = await self.invitation_repository.get_by_id(invitation_id)

        if not invitation:
            raise InvitationNotFoundError()

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError()

        return await self.invitation_repository.delete(invitation_id)


class ResendInvitationUseCase:
    """Use case to resend an invitation email."""

    def __init__(
        self,
        invitation_repository: InvitationRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self.invitation_repository = invitation_repository
        self.email_service = email_service

    async def execute(self, invitation_id: UUID) -> Invitation:
        """Resend invitation email with new token and expiry."""
        invitation = await self.invitation_repository.get_by_id(invitation_id)

        if not invitation:
            raise InvitationNotFoundError()

        if invitation.is_accepted:
            raise InvitationAlreadyAcceptedError()

        # Generate new token and reset expiry
        new_token = secrets.token_urlsafe(32)
        new_invitation = Invitation.create(
            email=invitation.email,
            role=invitation.role,
            invited_by=invitation.invited_by,
            token=new_token,
            validity_hours=48,
            boond_resource_id=invitation.boond_resource_id,
            manager_boond_id=invitation.manager_boond_id,
            phone=invitation.phone,
        )
        new_invitation.id = invitation.id  # Keep same ID

        saved_invitation = await self.invitation_repository.save(new_invitation)

        # Send invitation email
        await self.email_service.send_invitation_email(
            to_email=str(invitation.email),
            token=new_token,
            role=str(invitation.role),
        )

        return saved_invitation


class ListPendingInvitationsUseCase:
    """Use case to list pending invitations."""

    def __init__(self, invitation_repository: InvitationRepositoryPort) -> None:
        self.invitation_repository = invitation_repository

    async def execute(self, skip: int = 0, limit: int = 100) -> list[Invitation]:
        """List all pending invitations."""
        return await self.invitation_repository.list_pending(skip=skip, limit=limit)
