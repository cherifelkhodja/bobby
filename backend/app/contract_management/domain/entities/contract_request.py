"""Contract request domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contract_management.domain.exceptions import InvalidContractStatusError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


@dataclass
class ContractRequest:
    """A contract request triggered by a Boond positioning.

    Follows a state machine with 14 statuses from webhook reception
    through to archival.
    """

    reference: str
    boond_positioning_id: int
    commercial_email: str
    id: UUID = field(default_factory=uuid4)
    boond_candidate_id: int | None = None
    boond_need_id: int | None = None
    third_party_id: UUID | None = None
    status: ContractRequestStatus = ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION
    third_party_type: str | None = None
    daily_rate: Decimal | None = None
    start_date: date | None = None
    client_name: str | None = None
    mission_description: str | None = None
    mission_location: str | None = None
    contractualization_contact_email: str | None = None
    contract_config: dict[str, Any] | None = None
    commercial_validated_at: datetime | None = None
    compliance_override: bool = False
    compliance_override_reason: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_transition_to(self, target: ContractRequestStatus) -> bool:
        """Check if the transition to target status is allowed."""
        return self.status.can_transition_to(target)

    def transition_to(self, target: ContractRequestStatus) -> None:
        """Perform a validated status transition.

        Args:
            target: The new status.

        Raises:
            InvalidContractStatusError: If the transition is invalid.
        """
        if not self.can_transition_to(target):
            raise InvalidContractStatusError(self.status.value, target.value)
        self.status = target
        self.updated_at = datetime.utcnow()

    def validate_commercial(
        self,
        *,
        third_party_type: str,
        daily_rate: Decimal,
        start_date: date,
        contact_email: str,
        client_name: str | None = None,
        mission_description: str | None = None,
        mission_location: str | None = None,
    ) -> None:
        """Apply commercial validation data and transition status.

        Args:
            third_party_type: Type of third party (freelance, sous_traitant, salarie).
            daily_rate: Daily rate in euros.
            start_date: Mission start date.
            contact_email: Contact email for contractualization.
            client_name: Client name.
            mission_description: Mission description.
            mission_location: Mission location.
        """
        self.third_party_type = third_party_type
        self.daily_rate = daily_rate
        self.start_date = start_date
        self.contractualization_contact_email = contact_email
        self.client_name = client_name
        self.mission_description = mission_description
        self.mission_location = mission_location
        self.commercial_validated_at = datetime.utcnow()
        self.transition_to(ContractRequestStatus.COMMERCIAL_VALIDATED)

    def redirect_to_payfit(self) -> None:
        """Redirect to PayFit for salarié type."""
        self.transition_to(ContractRequestStatus.REDIRECTED_PAYFIT)

    def set_contract_config(self, config: dict[str, Any]) -> None:
        """Set contract configuration and transition to configuring.

        Args:
            config: Contract configuration dictionary.
        """
        self.contract_config = config
        self.transition_to(ContractRequestStatus.CONFIGURING_CONTRACT)

    def override_compliance(self, reason: str) -> None:
        """Override compliance check with a reason.

        Args:
            reason: Justification for the override.
        """
        self.compliance_override = True
        self.compliance_override_reason = reason
        self.updated_at = datetime.utcnow()
