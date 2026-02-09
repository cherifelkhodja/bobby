"""PDF converter port interface for document conversion."""

from abc import ABC, abstractmethod
from pathlib import Path


class PDFConverterPort(ABC):
    """Interface for document to PDF conversion.

    This port defines the contract for converting documents
    (Excel, Word) to PDF format using LibreOffice or similar tools.
    """

    @abstractmethod
    async def convert_to_pdf(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> Path:
        """Convert a document to PDF.

        Args:
            input_path: Path to input document (xlsx, docx, etc.).
            output_path: Optional output path. If not provided,
                        uses input path with .pdf extension.

        Returns:
            Path to the generated PDF file.

        Raises:
            PDFConversionError: If conversion fails.
            FileNotFoundError: If input file doesn't exist.
        """
        ...

    @abstractmethod
    async def convert_bytes_to_pdf(
        self,
        content: bytes,
        input_format: str,
        output_path: Path,
    ) -> Path:
        """Convert document bytes to PDF.

        Args:
            content: Document content as bytes.
            input_format: Input format extension (e.g., 'xlsx', 'docx').
            output_path: Path where PDF should be saved.

        Returns:
            Path to the generated PDF file.

        Raises:
            PDFConversionError: If conversion fails.
        """
        ...

    @abstractmethod
    async def merge_pdfs(
        self,
        pdf_paths: list[Path],
        output_path: Path,
    ) -> Path:
        """Merge multiple PDFs into one.

        Args:
            pdf_paths: List of PDF file paths to merge.
            output_path: Path for the merged PDF.

        Returns:
            Path to the merged PDF file.

        Raises:
            PDFConversionError: If merge fails.
            FileNotFoundError: If any input file doesn't exist.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the PDF conversion service is available.

        Returns:
            True if LibreOffice/conversion tool is available.
        """
        ...
