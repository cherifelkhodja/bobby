"""HTML → PDF contract generator using WeasyPrint + Jinja2."""

import re
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


def _md_inline(text: str) -> str:
    """Convert inline markdown to HTML (bold only)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)


def _format_capital(value: str) -> str:
    """Format capital with thousand separators and € symbol.

    '10000' → '10 000 €', '752000' → '752 000 €', already formatted → kept.
    """
    if not value:
        return value
    # If already contains €, return as-is
    if "€" in value:
        return value
    # Extract digits only
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return value
    # Format with space as thousand separator
    formatted = f"{int(digits):,}".replace(",", " ")
    return f"{formatted} €"


def _format_siren(value: str) -> str:
    """Format SIREN/RCS number as NNN NNN NNN.

    '842799959' → '842 799 959', '802082560' → '802 082 560'.
    """
    if not value:
        return value
    digits = re.sub(r"[^\d]", "", value)
    # Only format if exactly 9 digits (SIREN)
    if len(digits) == 9:
        return f"{digits[:3]} {digits[3:6]} {digits[6:9]}"
    return value


_CIVILITY_MAP = {
    "Mme": "Madame",
    "mme": "Madame",
    "MME": "Madame",
    "M.": "Monsieur",
    "M": "Monsieur",
    "Mr": "Monsieur",
    "mr": "Monsieur",
    "MR": "Monsieur",
}


def _format_civility(value: str) -> str:
    """Expand abbreviated civility to full form.

    'Mme' → 'Madame', 'M.' → 'Monsieur'.
    """
    if not value:
        return value
    return _CIVILITY_MAP.get(value.strip(), value)


def _expand_civility_in_name(value: str) -> str:
    """Expand abbreviated civility prefix in a full name.

    'Mme Selma HIZEM' → 'Madame Selma HIZEM'
    'M. Jean DUPONT' → 'Monsieur Jean DUPONT'
    """
    if not value:
        return value
    for abbr, full in _CIVILITY_MAP.items():
        prefix = abbr + " "
        if value.startswith(prefix):
            return full + " " + value[len(prefix) :]
    return value


# ── Identité visuelle (charte « Éditorial ») ─────────────────────────────────
# Palettes reprises de la maquette Claude Design « Contrat de sous-traitance ».
# Clé = fragment recherché dans le nom de la société émettrice (minuscules).
_BRAND_THEMES: dict[str, dict[str, str]] = {
    "craftmania": {
        "brand": "#e24a1a",
        "brand_strong": "#c1301c",
        "brand_tint": "#fbede6",
        "brand_grad": "linear-gradient(118deg,#ff8702,#e7521c 52%,#c50b2a)",
    },
    "leonum": {
        "brand": "#e95a6b",
        "brand_strong": "#ce4257",
        "brand_tint": "#fceced",
        "brand_grad": "linear-gradient(118deg,#f58393,#e95a6b 54%,#d23b52)",
    },
    "wohm": {
        "brand": "#2e9acd",
        "brand_strong": "#1f7fae",
        "brand_tint": "#e9f4fb",
        "brand_grad": "linear-gradient(118deg,#55b5e2,#2e9acd 52%,#176e9d)",
    },
}


def _parse_hex(value: str) -> tuple[int, int, int] | None:
    """Parse '#rgb' or '#rrggbb' into an (r, g, b) tuple, or None if unparsable."""
    if not value:
        return None
    digits = value.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    if len(digits) != 6:
        return None
    try:
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    except ValueError:
        return None


def _shade(rgb: tuple[int, int, int], ratio: float) -> str:
    """Blend a colour toward black (ratio < 0) or white (ratio > 0).

    ratio=-0.2 darkens by 20 %, ratio=0.9 gives a 90 %-white tint.
    """
    target = 255 if ratio > 0 else 0
    amount = abs(ratio)
    channels = (round(c + (target - c) * amount) for c in rgb)
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in channels)


def _resolve_brand_theme(company_name: str, color_code: str) -> dict[str, str]:
    """Return the brand colour set for the issuing company.

    Known brands use the palette hand-tuned in the design; any other company
    gets a coherent palette derived from its configured ``color_code`` so a
    newly created company still renders a correctly branded contract.
    """
    lower = (company_name or "").lower()
    for keyword, theme in _BRAND_THEMES.items():
        if keyword in lower:
            return dict(theme)

    rgb = _parse_hex(color_code)
    if not rgb:
        return dict(_BRAND_THEMES["craftmania"])

    strong = _shade(rgb, -0.18)
    return {
        "brand": "#" + "".join(f"{c:02x}" for c in rgb),
        "brand_strong": strong,
        "brand_tint": _shade(rgb, 0.92),
        "brand_grad": (
            f"linear-gradient(118deg,{_shade(rgb, 0.22)},"
            f"{'#' + ''.join(f'{c:02x}' for c in rgb)} 52%,{_shade(rgb, -0.3)})"
        ),
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

        # Inject the brand palette the template interpolates into its CSS.
        # Done here rather than in the use case so every caller (including the
        # ones building a context by hand) gets a correctly branded contract.
        theme = _resolve_brand_theme(
            template_context.get("issuer_company_name", ""),
            template_context.get("issuer_color_code", ""),
        )
        for key, value in theme.items():
            template_context.setdefault(key, value)

        # Render HTML
        env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        # Disable autoescape for the template since we use | safe manually
        env.autoescape = False
        env.filters["md"] = _md_inline
        env.filters["capital"] = _format_capital
        env.filters["siren"] = _format_siren
        env.filters["civility"] = _format_civility
        env.filters["expand_civility"] = _expand_civility_in_name
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
