"""HTML → PDF contract generator using WeasyPrint + Jinja2."""

import base64
import io
import os
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Path to the Jinja2 HTML template
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates"
TEMPLATE_NAME = "contrat_at.html"

# Path to the Gemini logo (resolved at import time)
_LOGO_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "frontend" / "public" / "logo-gemini.png"


def _load_logo_b64() -> str:
    """Load the Gemini logo as a base64-encoded string."""
    # Try the frontend public directory first (local dev)
    if _LOGO_PATH.exists():
        with open(_LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()

    # Fallback: look for it relative to the app directory (Docker)
    app_dir = Path(__file__).parent.parent.parent.parent.parent
    for candidate in [
        app_dir / "static" / "logo-gemini.png",
        app_dir / "logo-gemini.png",
    ]:
        if candidate.exists():
            with open(candidate, "rb") as f:
                return base64.b64encode(f.read()).decode()

    logger.warning("gemini_logo_not_found", searched=str(_LOGO_PATH))
    return ""


# Cache logo at module level (loaded once)
_LOGO_B64: str | None = None


def _get_logo_b64() -> str:
    global _LOGO_B64
    if _LOGO_B64 is None:
        _LOGO_B64 = _load_logo_b64()
    return _LOGO_B64


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

        # Inject logo
        template_context.setdefault("logo_b64", _get_logo_b64())

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
