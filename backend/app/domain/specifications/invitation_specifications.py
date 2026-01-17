"""
Invitation-related specifications.

Business rules for filtering and validating invitations.
"""

from datetime import datetime
from typing import Optional

from ..entities import Invitation
from ..value_objects import UserRole
from .base import Specification


class PendingInvitationSpecification(Specification[Invitation]):
    """
    Specification for pending (not accepted) invitations.
    A pending invitation is one that has not been accepted yet.
    """

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return not invitation.is_accepted


class ExpiredInvitationSpecification(Specification[Invitation]):
    """
    Specification for expired invitations.
    An invitation is expired if its expiry date has passed.
    """

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return invitation.is_expired


class ValidInvitationSpecification(Specification[Invitation]):
    """
    Specification for valid invitations.
    A valid invitation is one that is not expired and not accepted.
    """

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return not invitation.is_expired and not invitation.is_accepted


class InvitationByEmailSpecification(Specification[Invitation]):
    """Specification for invitations sent to a specific email."""

    def __init__(self, email: str):
        self._email = email.lower()

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return str(invitation.email).lower() == self._email

    @property
    def email(self) -> str:
        return self._email


class InvitationByRoleSpecification(Specification[Invitation]):
    """Specification for invitations for a specific role."""

    def __init__(self, role: UserRole):
        self._role = role

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return invitation.role == self._role

    @property
    def role(self) -> UserRole:
        return self._role


class InvitationByInviterSpecification(Specification[Invitation]):
    """Specification for invitations sent by a specific user."""

    def __init__(self, inviter_id: str):
        self._inviter_id = inviter_id

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return str(invitation.invited_by) == self._inviter_id


class RecentInvitationSpecification(Specification[Invitation]):
    """
    Specification for invitations created within a certain time period.
    Useful for rate limiting invitation sending.
    """

    def __init__(self, hours: int = 24):
        from datetime import timedelta
        self._cutoff = datetime.utcnow() - timedelta(hours=hours)

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        if hasattr(invitation, "created_at") and invitation.created_at:
            return invitation.created_at >= self._cutoff
        return False


class CanResendInvitationSpecification(Specification[Invitation]):
    """
    Specification for invitations that can be resent.
    An invitation can be resent if it is not accepted.
    """

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return not invitation.is_accepted


class CanAcceptInvitationSpecification(Specification[Invitation]):
    """
    Specification for invitations that can be accepted.
    An invitation can be accepted if it is not expired and not already accepted.
    """

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return not invitation.is_expired and not invitation.is_accepted
