"""Status enums for quotation generation."""

from enum import Enum


class BatchStatus(str, Enum):
    """Status of a quotation generation batch.

    Attributes:
        PENDING: Batch created, awaiting generation start.
        PROCESSING: Batch is being processed.
        COMPLETED: All quotations generated successfully.
        PARTIAL: Some quotations failed.
        FAILED: All quotations failed.
        EXPIRED: Batch has expired and been cleaned up.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    EXPIRED = "expired"

    def is_terminal(self) -> bool:
        """Check if this is a terminal status.

        Returns:
            True if batch processing is complete (success or failure).
        """
        return self in (
            BatchStatus.COMPLETED,
            BatchStatus.PARTIAL,
            BatchStatus.FAILED,
            BatchStatus.EXPIRED,
        )

    def is_success(self) -> bool:
        """Check if this is a successful status.

        Returns:
            True if all quotations were generated.
        """
        return self == BatchStatus.COMPLETED


class QuotationStatus(str, Enum):
    """Status of a single quotation generation.

    Attributes:
        PENDING: Quotation awaiting generation.
        CREATING_BOOND: Creating quotation in BoondManager.
        DOWNLOADING_PDF: Downloading PDF from BoondManager.
        FILLING_TEMPLATE: Filling Excel template.
        CONVERTING_PDF: Converting Excel to PDF.
        MERGING_PDF: Merging PDFs.
        COMPLETED: Quotation generated successfully.
        FAILED: Quotation generation failed.
    """

    PENDING = "pending"
    CREATING_BOOND = "creating_boond"
    DOWNLOADING_PDF = "downloading_pdf"
    FILLING_TEMPLATE = "filling_template"
    CONVERTING_PDF = "converting_pdf"
    MERGING_PDF = "merging_pdf"
    COMPLETED = "completed"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """Check if this is a terminal status.

        Returns:
            True if quotation processing is complete.
        """
        return self in (QuotationStatus.COMPLETED, QuotationStatus.FAILED)

    def get_display_message(self, resource_name: str = "") -> str:
        """Get a user-friendly status message.

        Args:
            resource_name: Name of the resource for context.

        Returns:
            Human-readable status message.
        """
        prefix = f"{resource_name} - " if resource_name else ""
        messages = {
            QuotationStatus.PENDING: "En attente",
            QuotationStatus.CREATING_BOOND: "Création devis BoondManager...",
            QuotationStatus.DOWNLOADING_PDF: "Téléchargement PDF devis...",
            QuotationStatus.FILLING_TEMPLATE: "Remplissage template Thales...",
            QuotationStatus.CONVERTING_PDF: "Conversion Excel → PDF...",
            QuotationStatus.MERGING_PDF: "Fusion des PDFs...",
            QuotationStatus.COMPLETED: "Terminé ✓",
            QuotationStatus.FAILED: "Échec ✗",
        }
        return prefix + messages.get(self, str(self.value))
