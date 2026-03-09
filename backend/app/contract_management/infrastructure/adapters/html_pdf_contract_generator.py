"""HTML → PDF contract generator using WeasyPrint + Jinja2."""

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Path to the Jinja2 HTML template
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates"
TEMPLATE_NAME = "contrat_at.html"

# Logos available in the templates directory (used as file references via base_url)
_KNOWN_LOGOS = {
    "craftmania": "logo-craftmania.png",
    "gemini": "logo-gemini.png",
}


def _get_logo_filename(company_name: str) -> str:
    """Return the logo filename (relative to TEMPLATE_DIR) for the given company name."""
    lower = company_name.lower() if company_name else ""
    for keyword, filename in _KNOWN_LOGOS.items():
        if keyword in lower:
            logo_path = TEMPLATE_DIR / filename
            if logo_path.exists():
                return filename
    # Fallback: first logo found in templates dir
    for filename in _KNOWN_LOGOS.values():
        if (TEMPLATE_DIR / filename).exists():
            return filename
    return ""


class HtmlPdfContractGenerator:
    """Generate a PDF contract from an HTML Jinja2 template using WeasyPrint.

    Replaces the DocxContractGenerator. Articles are injected from the
    database via the template context, allowing admin-editable content.
    """

    def __init__(self, template_dir: Path = TEMPLATE_DIR) -> None:
        self._template_dir = template_dir

    async def generate_draft(
        self,
        template_context: dict[str, Any],
    ) -> bytes:
        """Generate a contract PDF.

        Args:
            template_context: Jinja2 variables including 'articles' list.

        Returns:
            Generated PDF content as bytes.
        """
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from weasyprint import HTML

        # Inject logo fallback via file reference if no base64 logo provided
        if "logo_b64" not in template_context and "logo_filename" not in template_context:
            company_name = template_context.get("issuer_company_name", "")
            filename = _get_logo_filename(company_name)
            if filename:
                template_context["logo_filename"] = filename

        # Render HTML
        env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        # Disable autoescape for the template since we use | safe manually
        env.autoescape = False
        template = env.get_template(TEMPLATE_NAME)
        html_content = template.render(**template_context)

        # Convert to PDF
        pdf_bytes = HTML(string=html_content, base_url=str(self._template_dir)).write_pdf()

        logger.info(
            "contract_pdf_generated",
            reference=template_context.get("reference"),
            size_bytes=len(pdf_bytes),
        )

        return pdf_bytes
