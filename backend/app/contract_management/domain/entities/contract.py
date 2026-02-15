"""Contract domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Contract:
    """A generated contract document linked to a contract request.

    Tracks the DOCX draft, signed PDF, YouSign procedure,
    and BoondManager purchase order.
    """

    contract_request_id: UUID
    third_party_id: UUID
    reference: str
    s3_key_draft: str
    id: UUID = field(default_factory=uuid4)
    version: int = 1
    s3_key_signed: str | None = None
    yousign_procedure_id: str | None = None
    yousign_status: str | None = None
    boond_purchase_order_id: int | None = None
    partner_comments: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    signed_at: datetime | None = None

    def mark_signed(self, s3_key_signed: str) -> None:
        """Mark the contract as signed.

        Args:
            s3_key_signed: S3 key of the signed PDF.
        """
        self.s3_key_signed = s3_key_signed
        self.signed_at = datetime.utcnow()
        self.yousign_status = "done"

    def update_yousign_status(self, status: str) -> None:
        """Update the YouSign procedure status.

        Args:
            status: The new YouSign status.
        """
        self.yousign_status = status

    @property
    def is_signed(self) -> bool:
        """Check if the contract has been signed."""
        return self.signed_at is not None
