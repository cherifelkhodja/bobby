"""Text extractors for PDF and DOCX files.

Implements CvTextExtractorPort for dependency inversion.
"""

import io
from typing import BinaryIO

from pypdf import PdfReader
from docx import Document


class PdfTextExtractor:
    """PDF text extractor implementing CvTextExtractorPort."""

    def extract(self, content: bytes) -> str:
        """Extract text from PDF content."""
        return extract_text_from_pdf(content)


class DocxTextExtractor:
    """DOCX text extractor implementing CvTextExtractorPort."""

    def extract(self, content: bytes) -> str:
        """Extract text from DOCX content."""
        return extract_text_from_docx(content)


def extract_text_from_pdf(file_content: bytes | BinaryIO) -> str:
    """Extract text content from a PDF file.

    Args:
        file_content: PDF file content as bytes or file-like object.

    Returns:
        Extracted text from all pages.

    Raises:
        ValueError: If the PDF cannot be read or is empty.
    """
    if isinstance(file_content, bytes):
        file_content = io.BytesIO(file_content)

    try:
        reader = PdfReader(file_content)
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        if not text_parts:
            raise ValueError("Le PDF ne contient pas de texte extractible")

        return "\n\n".join(text_parts)
    except Exception as e:
        if "texte extractible" in str(e):
            raise
        raise ValueError(f"Erreur lors de la lecture du PDF: {str(e)}")


def extract_text_from_docx(file_content: bytes | BinaryIO) -> str:
    """Extract text content from a DOCX file.

    Args:
        file_content: DOCX file content as bytes or file-like object.

    Returns:
        Extracted text from all paragraphs and tables.

    Raises:
        ValueError: If the DOCX cannot be read or is empty.
    """
    if isinstance(file_content, bytes):
        file_content = io.BytesIO(file_content)

    try:
        document = Document(file_content)
        text_parts = []

        # Extract text from paragraphs
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Extract text from tables
        for table in document.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text_parts.append(" | ".join(row_text))

        if not text_parts:
            raise ValueError("Le document Word ne contient pas de texte extractible")

        return "\n\n".join(text_parts)
    except Exception as e:
        if "texte extractible" in str(e):
            raise
        raise ValueError(f"Erreur lors de la lecture du document Word: {str(e)}")
