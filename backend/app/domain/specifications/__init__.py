"""
Specification Pattern implementation.

The Specification pattern encapsulates business rules that can be combined
and reused. It provides a composable way to express complex selection criteria.

Example usage:
    # Simple specifications
    active_users = IsActiveSpecification()
    admin_users = HasRoleSpecification(UserRole.ADMIN)

    # Composite specification
    active_admins = active_users.and_(admin_users)

    # Use with repository
    users = await user_repository.find_by_specification(active_admins)
"""

from .base import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)
from .cooptation_specifications import (
    CooptationByOpportunitySpecification,
    CooptationByStatusSpecification,
    CooptationBySubmitterSpecification,
    PendingCooptationsSpecification,
)
from .invitation_specifications import (
    ExpiredInvitationSpecification,
    InvitationByEmailSpecification,
    PendingInvitationSpecification,
)
from .user_specifications import (
    HasRoleSpecification,
    IsActiveUserSpecification,
    IsVerifiedUserSpecification,
    UserEmailContainsSpecification,
)

__all__ = [
    # Base
    "Specification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    # User
    "IsActiveUserSpecification",
    "IsVerifiedUserSpecification",
    "HasRoleSpecification",
    "UserEmailContainsSpecification",
    # Cooptation
    "CooptationByStatusSpecification",
    "CooptationBySubmitterSpecification",
    "CooptationByOpportunitySpecification",
    "PendingCooptationsSpecification",
    # Invitation
    "PendingInvitationSpecification",
    "ExpiredInvitationSpecification",
    "InvitationByEmailSpecification",
]
