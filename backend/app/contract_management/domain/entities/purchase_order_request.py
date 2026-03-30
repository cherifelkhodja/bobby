"""Purchase order request domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contract_management.domain.exceptions import InvalidContractStatusError
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)


@dataclass
class PurchaseOrderRequest:
    """A purchase order request for an existing framework contract.

    Simplified workflow: validation → compliance check → BDC creation.
    Used when a supplier already has an active framework contract (contrat cadre).
    """

    framework_contract_id: UUID
    boond_positioning_id: int
    commercial_email: str
    reference: str  # PORBDC-YYYY-NNNN
    id: UUID = field(default_factory=uuid4)
    boond_candidate_id: int | None = None
    boond_consultant_type: str | None = None
    boond_need_id: int | None = None
    third_party_id: UUID | None = None
    status: PurchaseOrderRequestStatus = PurchaseOrderRequestStatus.PENDING_VALIDATION
    daily_rate: Decimal | None = None
    quantity_sold: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    client_name: str | None = None
    mission_title: str | None = None
    consultant_civility: str | None = None
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    consultant_email: str | None = None
    consultant_phone: str | None = None
    # Link to the PurchaseOrder once created
    purchase_order_id: UUID | None = None
    # Link to original ContractRequest if converted
    original_contract_request_id: UUID | None = None
    status_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_transition_to(self, target: PurchaseOrderRequestStatus) -> bool:
        """Check if the transition to target status is allowed."""
        return self.status.can_transition_to(target)

    def transition_to(self, target: PurchaseOrderRequestStatus) -> None:
        """Perform a validated status transition."""
        if not self.can_transition_to(target):
            raise InvalidContractStatusError(self.status.value, target.value)
        now = datetime.utcnow()
        self.status_history.append({"status": target.value, "entered_at": now.isoformat()})
        self.status = target
        self.updated_at = now

    def validate(
        self,
        *,
        daily_rate: Decimal,
        start_date: date,
        end_date: date | None = None,
        quantity_sold: int | None = None,
        client_name: str | None = None,
        mission_title: str | None = None,
    ) -> None:
        """Apply commercial validation data and transition to VALIDATED."""
        self.daily_rate = daily_rate
        self.start_date = start_date
        self.end_date = end_date
        self.quantity_sold = quantity_sold
        self.client_name = client_name
        self.mission_title = mission_title
        self.transition_to(PurchaseOrderRequestStatus.VALIDATED)

    @property
    def consultant_full_name(self) -> str | None:
        """Return the consultant's full name."""
        parts = [self.consultant_first_name, self.consultant_last_name]
        name = " ".join(p for p in parts if p)
        return name or None
