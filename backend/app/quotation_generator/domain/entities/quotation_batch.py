"""QuotationBatch entity representing a batch processing job."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.quotation_generator.domain.entities.quotation import Quotation
from app.quotation_generator.domain.value_objects import BatchStatus, QuotationStatus


@dataclass
class QuotationBatch:
    """A batch of quotations being processed together.

    This entity tracks the overall progress of batch processing,
    including individual quotation states and the final ZIP file.

    Attributes:
        id: Unique batch identifier.
        user_id: ID of the admin who initiated the batch.
        quotations: List of quotations in this batch.
        status: Current batch processing status.
        created_at: When the batch was created.
        started_at: When processing started.
        completed_at: When processing finished.
        zip_file_path: Path to the generated ZIP file.
        error_message: Error message if batch failed.
    """

    user_id: UUID
    quotations: list[Quotation] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    merged_pdf_path: str | None = None  # All quotations merged into one PDF
    zip_file_path: str | None = None  # ZIP archive with individual PDFs
    error_message: str | None = None

    @property
    def total_count(self) -> int:
        """Get total number of quotations in batch.

        Returns:
            Number of quotations.
        """
        return len(self.quotations)

    @property
    def completed_count(self) -> int:
        """Get number of completed quotations.

        Returns:
            Number of quotations with COMPLETED status.
        """
        return sum(1 for q in self.quotations if q.status == QuotationStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Get number of failed quotations.

        Returns:
            Number of quotations with FAILED status.
        """
        return sum(1 for q in self.quotations if q.status == QuotationStatus.FAILED)

    @property
    def pending_count(self) -> int:
        """Get number of pending quotations.

        Returns:
            Number of quotations with PENDING status.
        """
        return sum(1 for q in self.quotations if q.status == QuotationStatus.PENDING)

    @property
    def progress_percentage(self) -> float:
        """Calculate processing progress percentage.

        Returns:
            Percentage of processed quotations (0-100).
        """
        if self.total_count == 0:
            return 0.0
        processed = self.completed_count + self.failed_count
        return (processed / self.total_count) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all quotations have been processed.

        Returns:
            True if no quotations are pending or in progress.
        """
        return all(
            q.status in (QuotationStatus.COMPLETED, QuotationStatus.FAILED) for q in self.quotations
        )

    @property
    def has_errors(self) -> bool:
        """Check if any quotation failed.

        Returns:
            True if at least one quotation failed.
        """
        return self.failed_count > 0

    def add_quotation(self, quotation: Quotation) -> None:
        """Add a quotation to the batch.

        Args:
            quotation: Quotation to add.
        """
        quotation.row_index = len(self.quotations)
        self.quotations.append(quotation)

    def get_quotation(self, quotation_id: UUID) -> Quotation | None:
        """Find a quotation by ID.

        Args:
            quotation_id: UUID of the quotation.

        Returns:
            Quotation if found, None otherwise.
        """
        for q in self.quotations:
            if q.id == quotation_id:
                return q
        return None

    def get_quotation_by_index(self, index: int) -> Quotation | None:
        """Get quotation by row index.

        Args:
            index: Row index (0-based).

        Returns:
            Quotation if index valid, None otherwise.
        """
        if 0 <= index < len(self.quotations):
            return self.quotations[index]
        return None

    def start_processing(self) -> None:
        """Mark batch as processing started."""
        self.status = BatchStatus.PROCESSING
        self.started_at = datetime.utcnow()

    def mark_completed(self, merged_pdf_path: str, zip_path: str | None = None) -> None:
        """Mark batch as successfully completed.

        Args:
            merged_pdf_path: Path to the merged PDF with all quotations.
            zip_path: Path to the ZIP archive with individual PDFs.
        """
        self.status = BatchStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.merged_pdf_path = merged_pdf_path
        self.zip_file_path = zip_path

    def mark_partial(self, merged_pdf_path: str, zip_path: str | None = None) -> None:
        """Mark batch as partially completed (some failed).

        Args:
            merged_pdf_path: Path to the merged PDF with all quotations.
            zip_path: Path to the ZIP archive with individual PDFs.
        """
        self.status = BatchStatus.PARTIAL
        self.completed_at = datetime.utcnow()
        self.merged_pdf_path = merged_pdf_path
        self.zip_file_path = zip_path

    def mark_failed(self, error: str) -> None:
        """Mark entire batch as failed.

        Args:
            error: Error message.
        """
        self.status = BatchStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error

    def validate_all(self) -> dict[int, list[str]]:
        """Run validation on all quotations.

        Returns:
            Dictionary mapping row index to list of errors.
        """
        errors: dict[int, list[str]] = {}
        for i, quotation in enumerate(self.quotations):
            quotation_errors = quotation.validate()
            if quotation_errors:
                errors[i] = quotation_errors
        return errors

    def to_progress_dict(self) -> dict:
        """Convert to progress tracking dictionary.

        Returns:
            Dictionary with progress information.
        """
        return {
            "batch_id": str(self.id),
            "status": self.status.value,
            "total": self.total_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "progress_percentage": round(self.progress_percentage, 1),
            "is_complete": self.is_complete,
            "has_errors": self.has_errors,
            "merged_pdf_path": self.merged_pdf_path,
            "zip_file_path": self.zip_file_path,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_preview_dict(self) -> dict:
        """Convert to preview dictionary for frontend.

        Returns:
            Dictionary with batch preview data.
        """
        return {
            "batch_id": str(self.id),
            "total_quotations": self.total_count,
            "quotations": [
                {
                    "row_index": q.row_index,
                    "resource_name": q.resource_name,
                    "resource_trigramme": q.resource_trigramme,
                    "resource_id": q.resource_id,
                    "opportunity_id": q.opportunity_id,
                    "company_name": q.company_name,
                    "company_id": q.company_id,
                    "company_detail_id": q.company_detail_id,
                    "contact_name": q.contact_name,
                    "contact_id": q.contact_id,
                    "quotation_date": (q.quotation_date or q.period.start_date).strftime(
                        "%d/%m/%Y"
                    ),  # Date du devis
                    "period": {
                        "start": q.period.format_start(),
                        "end": q.period.format_end(),
                    },
                    "period_name": q.period_name,
                    "tjm": q.tjm.to_float(),
                    "quantity": q.quantity,
                    "total_ht": q.total_ht.to_float(),
                    "total_ttc": q.total_ttc.to_float(),
                    "c22_domain": q.c22_domain,
                    "c22_activity": q.c22_activity,
                    "complexity": q.complexity,
                    "max_price": q.max_price.to_float(),
                    "sow_reference": q.sow_reference,
                    "object_of_need": q.object_of_need,
                    "need_title": q.need_title,
                    "comments": q.comments,
                    "start_project": q.start_project.isoformat(),
                    # Additional Thales fields
                    "eacq_number": q.eacq_number,
                    "is_renewal": q.is_renewal,
                    "in_situ_ratio": q.in_situ_ratio,
                    "subcontracting": q.subcontracting,
                    "tier2_supplier": q.tier2_supplier,
                    "tier3_supplier": q.tier3_supplier,
                    "is_valid": q.is_valid,
                    "validation_errors": q.validation_errors,
                }
                for q in self.quotations
            ],
        }

    def __str__(self) -> str:
        """Format as readable string."""
        return f"QuotationBatch({self.id}: {self.completed_count}/{self.total_count})"
