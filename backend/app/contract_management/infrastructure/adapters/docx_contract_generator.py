"""DOCX contract generator using docxtpl."""

import io
from typing import Any

import structlog

logger = structlog.get_logger()

DEFAULT_TEMPLATE_PATH = "templates/contrat_at.docx"


class DocxContractGenerator:
    """Generate contract documents from DOCX templates using docxtpl.

    Uses Jinja2 variables in the DOCX template and fills them with
    contract data including dynamic article numbering.
    """

    def __init__(self, template_path: str = DEFAULT_TEMPLATE_PATH) -> None:
        self._template_path = template_path

    async def generate_draft(
        self,
        template_context: dict[str, Any],
    ) -> bytes:
        """Generate a contract draft document.

        Args:
            template_context: Variables for the DOCX template.

        Returns:
            Generated DOCX content as bytes.
        """
        from docxtpl import DocxTemplate

        from app.contract_management.domain.services.article_numbering import (
            compute_article_numbers,
        )

        try:
            doc = DocxTemplate(self._template_path)
        except FileNotFoundError:
            logger.error(
                "contract_template_not_found",
                template_path=self._template_path,
            )
            raise ValueError(f"Template de contrat introuvable : {self._template_path}")

        # Compute article numbers
        article_numbers = compute_article_numbers(template_context)
        template_context["articles"] = article_numbers

        doc.render(template_context)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        logger.info(
            "contract_draft_generated",
            template=self._template_path,
            context_keys=list(template_context.keys()),
        )

        return buffer.read()
