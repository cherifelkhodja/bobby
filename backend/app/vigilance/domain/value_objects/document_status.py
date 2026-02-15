"""Document status value object with state machine transitions."""

from enum import Enum


class DocumentStatus(str, Enum):
    """Status of a vigilance document through its lifecycle."""

    REQUESTED = "requested"
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"

    @property
    def allowed_transitions(self) -> frozenset["DocumentStatus"]:
        """Return the set of statuses this status can transition to."""
        transitions: dict[DocumentStatus, frozenset[DocumentStatus]] = {
            DocumentStatus.REQUESTED: frozenset({DocumentStatus.RECEIVED}),
            DocumentStatus.RECEIVED: frozenset({
                DocumentStatus.VALIDATED,
                DocumentStatus.REJECTED,
            }),
            DocumentStatus.VALIDATED: frozenset({
                DocumentStatus.EXPIRING_SOON,
                DocumentStatus.EXPIRED,
            }),
            DocumentStatus.REJECTED: frozenset({DocumentStatus.REQUESTED}),
            DocumentStatus.EXPIRING_SOON: frozenset({
                DocumentStatus.EXPIRED,
                DocumentStatus.VALIDATED,
            }),
            DocumentStatus.EXPIRED: frozenset({DocumentStatus.REQUESTED}),
        }
        return transitions.get(self, frozenset())

    def can_transition_to(self, target: "DocumentStatus") -> bool:
        """Check if transition to target status is allowed.

        Args:
            target: The target status.

        Returns:
            True if the transition is valid.
        """
        return target in self.allowed_transitions
