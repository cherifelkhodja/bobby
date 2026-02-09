"""LibreOffice adapter implementing PDFConverterPort."""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from PyPDF2 import PdfMerger

from app.quotation_generator.domain.exceptions import PDFConversionError
from app.quotation_generator.domain.ports import PDFConverterPort

logger = logging.getLogger(__name__)


class LibreOfficeAdapter(PDFConverterPort):
    """LibreOffice headless adapter for document to PDF conversion.

    This adapter uses LibreOffice in headless mode to convert
    documents (Excel, Word) to PDF format.
    """

    def __init__(
        self,
        libreoffice_path: str | None = None,
        temp_dir: Path | None = None,
    ) -> None:
        """Initialize adapter.

        Args:
            libreoffice_path: Path to LibreOffice binary.
                            Auto-detected if not provided.
            temp_dir: Directory for temporary files.
                     Uses system temp if not provided.
        """
        self.libreoffice_path = libreoffice_path or self._find_libreoffice()
        self.temp_dir = temp_dir or Path(tempfile.gettempdir())

    def _find_libreoffice(self) -> str:
        """Find LibreOffice binary path.

        Returns:
            Path to LibreOffice binary.

        Raises:
            PDFConversionError: If LibreOffice not found.
        """
        # Common paths for LibreOffice
        paths = [
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
            "/usr/local/bin/libreoffice",
            "/usr/local/bin/soffice",
            "/opt/libreoffice/program/soffice",
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        ]

        for path in paths:
            if shutil.which(path) or Path(path).exists():
                logger.info(f"Found LibreOffice at: {path}")
                return path

        # Try to find via which
        soffice = shutil.which("soffice")
        if soffice:
            return soffice

        libreoffice = shutil.which("libreoffice")
        if libreoffice:
            return libreoffice

        logger.warning("LibreOffice not found in common paths")
        return "soffice"  # Will fail at runtime if not available

    async def convert_to_pdf(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> Path:
        """Convert a document to PDF using LibreOffice.

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
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Determine output path
        if output_path is None:
            output_path = input_path.with_suffix(".pdf")

        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [
            self.libreoffice_path,
            "--headless",
            "--invisible",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]

        logger.info(f"Converting {input_path.name} to PDF")
        logger.debug(f"Command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120.0,  # 2 minute timeout
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"LibreOffice conversion failed: {error_msg}")
                raise PDFConversionError(f"LibreOffice conversion failed: {error_msg}")

            # LibreOffice outputs to outdir with same name but .pdf extension
            expected_output = output_dir / f"{input_path.stem}.pdf"

            if not expected_output.exists():
                raise PDFConversionError(f"PDF file not created: {expected_output}")

            # Rename if different from requested output_path
            if expected_output != output_path:
                expected_output.rename(output_path)

            logger.info(f"Successfully converted to {output_path}")
            return output_path

        except TimeoutError:
            raise PDFConversionError("LibreOffice conversion timed out")
        except Exception as e:
            if isinstance(e, PDFConversionError):
                raise
            raise PDFConversionError(f"Conversion error: {str(e)}") from e

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
        # Create temporary input file
        temp_input = self.temp_dir / f"temp_input.{input_format}"

        try:
            temp_input.write_bytes(content)
            return await self.convert_to_pdf(temp_input, output_path)
        finally:
            # Clean up temp file
            if temp_input.exists():
                temp_input.unlink()

    async def merge_pdfs(
        self,
        pdf_paths: list[Path],
        output_path: Path,
    ) -> Path:
        """Merge multiple PDFs into one using PyPDF2.

        Args:
            pdf_paths: List of PDF file paths to merge.
            output_path: Path for the merged PDF.

        Returns:
            Path to the merged PDF file.

        Raises:
            PDFConversionError: If merge fails.
            FileNotFoundError: If any input file doesn't exist.
        """
        # Validate all inputs exist
        for pdf_path in pdf_paths:
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not pdf_paths:
            raise PDFConversionError("No PDF files to merge")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            merger = PdfMerger()

            for pdf_path in pdf_paths:
                logger.debug(f"Adding {pdf_path.name} to merger")
                merger.append(str(pdf_path))

            merger.write(str(output_path))
            merger.close()

            logger.info(f"Merged {len(pdf_paths)} PDFs into {output_path}")
            return output_path

        except Exception as e:
            raise PDFConversionError(f"PDF merge failed: {str(e)}") from e

    async def is_available(self) -> bool:
        """Check if LibreOffice is available.

        Returns:
            True if LibreOffice is available and working.
        """
        try:
            cmd = [self.libreoffice_path, "--version"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0,
            )

            if process.returncode == 0:
                version = stdout.decode().strip()
                logger.info(f"LibreOffice available: {version}")
                return True

            return False

        except Exception as e:
            logger.warning(f"LibreOffice not available: {e}")
            return False
