"""Framework contract (contrat cadre) domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.contract_management.domain.value_objects.framework_contract_status import (
    FrameworkContractStatus,
)


@dataclass
class FrameworkContract:
    """A framework contract linking a supplier to a company.

    One supplier (ThirdParty) has at most one active framework contract
    per issuing company. Once signed, subsequent contract requests for
    the same supplier skip the full process and go through the fast path
    (compliance check + purchase order creation only).
    """

    third_party_id: UUID
    company_id: UUID
    original_contract_request_id: UUID
    reference: str
    id: UUID = field(default_factory=uuid4)
    original_contract_id: UUID | None = None
    s3_key_signed: str | None = None
    signed_at: datetime | None = None
    status: FrameworkContractStatus = FrameworkContractStatus.ACTIVE
    expires_at: datetime | None = None
    tacit_renewal: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_usable(self) -> bool:
        """Whether this framework contract can be used for new purchase orders."""
        return self.status.is_usable

    def terminate(self) -> None:
        """Terminate this framework contract."""
        self.status = FrameworkContractStatus.TERMINATED
        self.updated_at = datetime.utcnow()

    def mark_expired(self) -> None:
        """Mark this framework contract as expired."""
        self.status = FrameworkContractStatus.EXPIRED
        self.updated_at = datetime.utcnow()

    def mark_expiring_soon(self) -> None:
        """Mark this framework contract as expiring soon."""
        self.status = FrameworkContractStatus.EXPIRING_SOON
        self.updated_at = datetime.utcnow()

    def renew(self, new_expires_at: datetime | None = None) -> None:
        """Renew this framework contract (tacit renewal)."""
        self.status = FrameworkContractStatus.ACTIVE
        self.expires_at = new_expires_at
        self.updated_at = datetime.utcnow()
