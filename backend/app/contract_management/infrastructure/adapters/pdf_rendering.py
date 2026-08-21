"""Rendu PDF partagé des documents contractuels (WeasyPrint + Jinja2).

Regroupe ce que le contrat, les chartes et les accusés de réception ont en
commun : les filtres de mise en forme, la palette de marque de la société
émettrice et la construction de l'environnement Jinja2.

Le `base_url` pointe sur le dossier des gabarits : sans lui WeasyPrint ne
résout ni les polices embarquées (`fonts/…`) ni les logos référencés par nom
de fichier, et substitue silencieusement une police de repli.
"""

import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Dossier des gabarits HTML (backend/templates).
TEMPLATE_DIR = Path(__file__).resolve().parents[4] / "templates"


def md_inline(text: str) -> str:
    """Convert inline markdown to HTML (bold only)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)


def format_capital(value: str) -> str:
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


def format_siren(value: str) -> str:
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


def format_civility(value: str) -> str:
    """Expand abbreviated civility to full form.

    'Mme' → 'Madame', 'M.' → 'Monsieur'.
    """
    if not value:
        return value
    return _CIVILITY_MAP.get(value.strip(), value)


def expand_civility_in_name(value: str) -> str:
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
BRAND_THEMES: dict[str, dict[str, str]] = {
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


def resolve_brand_theme(company_name: str, color_code: str) -> dict[str, str]:
    """Return the brand colour set for the issuing company.

    Known brands use the palette hand-tuned in the design; any other company
    gets a coherent palette derived from its configured ``color_code`` so a
    newly created company still renders a correctly branded contract.
    """
    lower = (company_name or "").lower()
    for keyword, theme in BRAND_THEMES.items():
        if keyword in lower:
            return dict(theme)

    rgb = _parse_hex(color_code)
    if not rgb:
        return dict(BRAND_THEMES["craftmania"])

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


def build_environment(template_dir: Path = TEMPLATE_DIR):
    """Return the Jinja2 environment the PDF templates are rendered with.

    A FileSystemLoader is required — the templates use ``{% extends %}`` and
    ``{% include %}`` to share the brand stylesheet and page furniture.
    Autoescaping stays off: the templates mark their own values with ``| safe``
    where markdown-ish article content is injected.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
    env.filters["md"] = md_inline
    env.filters["capital"] = format_capital
    env.filters["siren"] = format_siren
    env.filters["civility"] = format_civility
    env.filters["expand_civility"] = expand_civility_in_name
    return env


def apply_brand_theme(context: dict[str, Any]) -> None:
    """Fill the brand palette the templates interpolate into their CSS.

    Values already present in the context win, so a caller can force a palette.
    """
    theme = resolve_brand_theme(
        context.get("issuer_company_name", ""),
        context.get("issuer_color_code", ""),
    )
    for key, value in theme.items():
        context.setdefault(key, value)


def render_pdf(
    template_name: str,
    context: dict[str, Any],
    template_dir: Path = TEMPLATE_DIR,
) -> bytes:
    """Render a template to PDF bytes, brand palette included."""
    from weasyprint import HTML

    apply_brand_theme(context)
    html_content = build_environment(template_dir).get_template(template_name).render(**context)
    pdf_bytes = HTML(string=html_content, base_url=str(template_dir)).write_pdf()

    logger.info(
        "pdf_rendered",
        template=template_name,
        reference=context.get("reference"),
        size_bytes=len(pdf_bytes),
    )
    return pdf_bytes
