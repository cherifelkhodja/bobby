"""Tests du gabarit PDF de contrat (charte « Éditorial ») et de sa palette."""

from pathlib import Path

import pytest

from app.contract_management.infrastructure.adapters.html_pdf_contract_generator import (
    TEMPLATE_DIR,
    TEMPLATE_NAME,
    HtmlPdfContractGenerator,
    _parse_hex,
    _resolve_brand_theme,
    _shade,
)

# Graisses embarquées : le gabarit les déclare toutes en @font-face et l'image
# Docker n'installe aucune des deux familles.
EXPECTED_FONTS = [
    f"{family}-{weight}.ttf"
    for family in ("SpaceGrotesk", "HankenGrotesk")
    for weight in (400, 500, 600, 700)
]


def _squash(text: str) -> str:
    """Retire toute espace du texte extrait du PDF.

    L'extraction réinsère les retours à la ligne de la mise en page et rend
    l'interlettrage (letter-spacing) sous forme d'espaces parasites : comparer
    sans espaces est le seul moyen fiable d'assertion sur le contenu.
    """
    return "".join(text.split())


class _Article:
    def __init__(self, key: str, title: str, content: str) -> None:
        self.article_key = key
        self.title = title
        self.content = content


class _Annexe:
    def __init__(self, key: str, title: str, content: str) -> None:
        self.annexe_key = key
        self.title = title
        self.content = content


def _context() -> dict:
    return {
        "issuer_company_name": "LEONUM",
        "issuer_legal_form": "SAS",
        "issuer_capital": "10000",
        "issuer_head_office": "54 avenue Hoche, 75008 Paris",
        "issuer_rcs_city": "Paris",
        "issuer_rcs_number": "842799959",
        "issuer_representative_is_entity": True,
        "issuer_representative_name": "SC Holding",
        "issuer_representative_quality": "Président",
        "issuer_representative_sub_name": "Mme Selma HIZEM",
        "issuer_representative_sub_quality": "Présidente",
        "issuer_signatory_name": "Mme Selma HIZEM",
        "issuer_color_code": "#e95a6b",
        "issuer_tva_number": "FR23842799959",
        "reference": "LEO-CC-0042",
        "contract_date": "21/08/2026",
        "partner_company_name": "AKEMA TECH",
        "partner_legal_form": "SASU",
        "partner_capital": "5000",
        "partner_head_office": "12 rue de la Paix, 75002 Paris",
        "partner_rcs_city": "Paris",
        "partner_rcs_number": "912345678",
        "partner_representative_civility": "M.",
        "partner_representative_name": "Karim BENALI",
        "partner_representative_title": "Président",
        "articles": [
            _Article("preambule", "Préambule", "La Société souhaite confier au Partenaire..."),
            _Article("objet", "Objet", "Le Contrat définit les conditions générales."),
            _Article(
                "financieres",
                "Conditions financières",
                "Le TJM est défini au BDC.\n\n- **Paiement** : 30 jours nets.\n- Pénalités de retard.",
            ),
        ],
        "annexes": [
            _Annexe(
                "conformite_sociale", "Conformité sociale", "- Extrait Kbis de moins de 3 mois"
            ),
        ],
    }


# ── Palette de marque ────────────────────────────────────────────────────────


def test_parse_hex_accepts_short_and_long_form():
    assert _parse_hex("#e24a1a") == (226, 74, 26)
    assert _parse_hex("#123") == (17, 34, 51)
    assert _parse_hex("e24a1a") == (226, 74, 26)


@pytest.mark.parametrize("value", ["", "notacolor", "#12", "#zzzzzz"])
def test_parse_hex_rejects_invalid_values(value):
    assert _parse_hex(value) is None


def test_shade_blends_toward_black_and_white():
    assert _shade((100, 100, 100), -1.0) == "#000000"
    assert _shade((100, 100, 100), 1.0) == "#ffffff"
    assert _shade((100, 100, 100), 0.0) == "#646464"


@pytest.mark.parametrize(
    ("company", "expected_brand"),
    [("CRAFTMANIA", "#e24a1a"), ("LEONUM", "#e95a6b"), ("WOHM", "#2e9acd")],
)
def test_known_brands_use_the_design_palette(company, expected_brand):
    """Les marques de la maquette gardent leurs couleurs, quel que soit color_code."""
    theme = _resolve_brand_theme(company, "#000000")
    assert theme["brand"] == expected_brand


def test_unknown_company_derives_a_palette_from_its_color_code():
    theme = _resolve_brand_theme("GEMINI CONSULTING", "#4BBEA8")
    assert theme["brand"] == "#4bbea8"
    # Teinte assombrie pour les aplats de texte, très claire pour les fonds.
    assert theme["brand_strong"] != theme["brand"]
    assert theme["brand_tint"].startswith("#f")
    assert theme["brand_grad"].startswith("linear-gradient(118deg,")


def test_unusable_color_code_falls_back_to_a_valid_palette():
    theme = _resolve_brand_theme("Société Inconnue", "pas-une-couleur")
    assert set(theme) == {"brand", "brand_strong", "brand_tint", "brand_grad"}
    assert theme["brand"].startswith("#")


# ── Gabarit ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("filename", EXPECTED_FONTS)
def test_embedded_font_is_present(filename):
    """Sans ces fichiers WeasyPrint substitue silencieusement une autre police."""
    assert (TEMPLATE_DIR / "fonts" / filename).is_file()


def test_template_declares_every_embedded_font():
    css = (TEMPLATE_DIR / TEMPLATE_NAME).read_text(encoding="utf-8")
    for filename in EXPECTED_FONTS:
        assert f"fonts/{filename}" in css


async def test_generate_draft_renders_a_multi_page_pdf():
    pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")
    pymupdf = pytest.importorskip("pymupdf", reason="pymupdf absent de cet environnement")

    pdf = await HtmlPdfContractGenerator().generate_draft(_context())

    assert pdf.startswith(b"%PDF")
    document = pymupdf.open(stream=pdf, filetype="pdf")
    # Couverture + corps, l'annexe forçant en plus un saut de page.
    assert document.page_count >= 3

    cover = _squash(document[0].get_text())
    assert _squash("Contrat cadre de sous-traitance") in cover
    assert "LEO-CC-0042" in cover
    assert _squash("AKEMA TECH") in cover
    # Mentions légales de l'émetteur en pied de couverture.
    assert _squash("R.C.S. Paris 842 799 959") in cover

    body = _squash("\n".join(page.get_text() for page in document))
    assert _squash("Entre les soussignés").upper() in body.upper()
    assert _squash("Conformité sociale") in body
    assert "Signatures" in body
    # Le préambule ne consomme pas de numéro : le premier article numéroté est « 1 Objet »
    # (les intitulés d'article sont capitalisés par la feuille de style).
    assert _squash("1Objet").lower() in body.lower()


async def test_generate_draft_injects_the_brand_palette():
    """Le contexte reçoit la palette même quand l'appelant ne la fournit pas."""
    pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")

    context = _context()
    await HtmlPdfContractGenerator().generate_draft(context)

    assert context["brand"] == "#e95a6b"
    assert context["brand_strong"] == "#ce4257"


async def test_generate_draft_keeps_a_caller_supplied_palette():
    pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")

    context = _context() | {"brand": "#000fff"}
    await HtmlPdfContractGenerator().generate_draft(context)

    assert context["brand"] == "#000fff"


def test_template_directory_is_packaged_next_to_the_generator():
    assert TEMPLATE_DIR.is_dir()
    assert (TEMPLATE_DIR / TEMPLATE_NAME).is_file()
    assert Path(TEMPLATE_DIR / "fonts").is_dir()
