"""Purchase order (bon de commande) domain entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


@dataclass
class PurchaseOrder:
    """A purchase order linked to a framework contract.

    Multiple purchase orders can exist per framework contract,
    one per consultant/mission/positioning.
    """

    framework_contract_id: UUID
    contract_request_id: UUID
    reference: str
    boond_positioning_id: int
    id: UUID = field(default_factory=uuid4)
    consultant_first_name: str | None = None
    consultant_last_name: str | None = None
    daily_rate: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    quantity: int | None = None
    boond_purchase_order_id: int | None = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    s3_key: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def consultant_full_name(self) -> str | None:
        """Return the consultant's full name."""
        parts = [self.consultant_first_name, self.consultant_last_name]
        name = " ".join(p for p in parts if p)
        return name or None

    def mark_active(self) -> None:
        """Mark this purchase order as active (synced to Boond)."""
        self.status = PurchaseOrderStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def close(self) -> None:
        """Close this purchase order."""
        self.status = PurchaseOrderStatus.CLOSED
        self.updated_at = datetime.utcnow()
