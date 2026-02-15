"""Vigilance document domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.vigilance.domain.exceptions import InvalidDocumentTransitionError
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType


@dataclass
class VigilanceDocument:
    """A legal/compliance document for a third party.

    Follows a state machine lifecycle:
    REQUESTED → RECEIVED → VALIDATED → EXPIRING_SOON → EXPIRED
                         → REJECTED → REQUESTED (new cycle)
    """

    third_party_id: UUID
    document_type: DocumentType
    id: UUID = field(default_factory=uuid4)
    status: DocumentStatus = DocumentStatus.REQUESTED
    s3_key: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    uploaded_at: datetime | None = None
    validated_at: datetime | None = None
    validated_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    expires_at: datetime | None = None
    auto_check_results: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_transition_to(self, target: DocumentStatus) -> bool:
        """Check if the document can transition to the target status.

        Args:
            target: The desired new status.

        Returns:
            True if the transition is allowed.
        """
        return self.status.can_transition_to(target)

    def _transition(self, target: DocumentStatus) -> None:
        """Perform a status transition with validation.

        Args:
            target: The new status.

        Raises:
            InvalidDocumentTransitionError: If the transition is not allowed.
        """
        if not self.can_transition_to(target):
            raise InvalidDocumentTransitionError(
                self.status.value, target.value
            )
        self.status = target
        self.updated_at = datetime.utcnow()

    def mark_received(
        self,
        s3_key: str,
        file_name: str,
        file_size: int,
    ) -> None:
        """Mark document as received after upload.

        Args:
            s3_key: The S3 storage key.
            file_name: Original file name.
            file_size: File size in bytes.
        """
        self._transition(DocumentStatus.RECEIVED)
        self.s3_key = s3_key
        self.file_name = file_name
        self.file_size = file_size
        self.uploaded_at = datetime.utcnow()

    def validate(self, validated_by: str, expires_at: datetime | None = None) -> None:
        """Validate the document.

        Args:
            validated_by: Email or name of the validator.
            expires_at: Optional expiration date for the document.
        """
        self._transition(DocumentStatus.VALIDATED)
        self.validated_at = datetime.utcnow()
        self.validated_by = validated_by
        self.expires_at = expires_at
        self.rejected_at = None
        self.rejection_reason = None

    def reject(self, reason: str) -> None:
        """Reject the document with a reason.

        Args:
            reason: The rejection reason.
        """
        self._transition(DocumentStatus.REJECTED)
        self.rejected_at = datetime.utcnow()
        self.rejection_reason = reason

    def mark_expiring_soon(self) -> None:
        """Mark validated document as expiring soon."""
        self._transition(DocumentStatus.EXPIRING_SOON)

    def mark_expired(self) -> None:
        """Mark document as expired."""
        self._transition(DocumentStatus.EXPIRED)

    def re_request(self) -> None:
        """Re-request the document after rejection or expiration."""
        self._transition(DocumentStatus.REQUESTED)
        self.s3_key = None
        self.file_name = None
        self.file_size = None
        self.uploaded_at = None
        self.validated_at = None
        self.validated_by = None
        self.rejected_at = None
        self.rejection_reason = None
        self.expires_at = None
        self.auto_check_results = None

    @property
    def is_valid(self) -> bool:
        """Check if the document is currently valid."""
        return self.status == DocumentStatus.VALIDATED

    @property
    def needs_attention(self) -> bool:
        """Check if the document requires ADV action."""
        return self.status in (
            DocumentStatus.RECEIVED,
            DocumentStatus.EXPIRING_SOON,
            DocumentStatus.EXPIRED,
        )
