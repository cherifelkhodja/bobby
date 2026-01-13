"""CV Transformation Log domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class CvTransformationLog:
    """CV Transformation Log entity tracking CV transformation operations."""

    user_id: UUID  # User who performed the transformation
    template_name: str  # Name of the template used
    original_filename: str  # Original CV filename
    success: bool  # Whether the transformation succeeded
    template_id: Optional[UUID] = None  # Reference to the template (nullable if deleted)
    error_message: Optional[str] = None  # Error message if failed
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_success(
        cls,
        user_id: UUID,
        template_id: UUID,
        template_name: str,
        original_filename: str,
    ) -> "CvTransformationLog":
        """Create a successful transformation log."""
        return cls(
            user_id=user_id,
            template_id=template_id,
            template_name=template_name,
            original_filename=original_filename,
            success=True,
        )

    @classmethod
    def create_failure(
        cls,
        user_id: UUID,
        template_name: str,
        original_filename: str,
        error_message: str,
        template_id: Optional[UUID] = None,
    ) -> "CvTransformationLog":
        """Create a failed transformation log."""
        return cls(
            user_id=user_id,
            template_id=template_id,
            template_name=template_name,
            original_filename=original_filename,
            success=False,
            error_message=error_message,
        )
