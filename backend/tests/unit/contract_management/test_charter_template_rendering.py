"""Tests des gabarits de chartes, accusés de réception et engagement."""

import pytest

from app.contract_management.application.use_cases.generate_charter_documents import (
    CHARTER_DOCUMENTS,
    documents_for,
)
from app.contract_management.infrastructure.adapters.pdf_rendering import (
    TEMPLATE_DIR,
    render_pdf,
)


def _squash(text: str) -> str:
    """Retire toute espace du texte extrait du PDF.

    L'extraction réinsère les retours à la ligne de la mise en page et rend
    l'interlettrage sous forme d'espaces parasites.
    """
    return "".join(text.split())


def _has(haystack: str, needle: str) -> bool:
    """Cherche `needle` dans un texte déjà compacté, sans tenir compte de la casse.

    Les intitulés sont capitalisés par `text-transform: uppercase` : la casse du
    texte extrait est celle du rendu, pas celle du gabarit.
    """
    return _squash(needle).lower() in haystack.lower()


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
        "issuer_representative_sub_quality": "Présidente",
        "issuer_signatory_name": "Mme Selma HIZEM",
        "issuer_tva_number": "FR23842799959",
        "issuer_color_code": "#e95a6b",
        "charter_version": "2026.1",
        "ethics_alert_email": "alerte-ethique@leonum.fr",
        "reference": "LEO-CC-0042",
        "consultant_first_name": "Karim",
        "consultant_last_name": "BENALI",
        "mission_title": "TMA Socle Data",
        "partner_company_name": "AKEMA TECH",
        "partner_representative_civility": "M.",
        "partner_representative_name": "Karim BENALI",
        "partner_representative_title": "Président",
    }


def _render(template: str):
    """Render a template and return (pdf_bytes, squashed_text, page_count)."""
    pymupdf = pytest.importorskip("pymupdf", reason="pymupdf absent de cet environnement")
    pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")

    pdf = render_pdf(template, _context())
    document = pymupdf.open(stream=pdf, filetype="pdf")
    text = _squash("\n".join(page.get_text() for page in document))
    return pdf, text, document.page_count


# ── Registre ─────────────────────────────────────────────────────────────────


def test_every_registered_document_has_its_template():
    for document in CHARTER_DOCUMENTS:
        assert (TEMPLATE_DIR / document.template).is_file(), document.key


def test_registry_keys_and_result_keys_are_unique():
    assert len({d.key for d in CHARTER_DOCUMENTS}) == len(CHARTER_DOCUMENTS)
    assert len({d.result_key for d in CHARTER_DOCUMENTS}) == len(CHARTER_DOCUMENTS)


def test_documents_are_split_between_consultant_and_partner():
    consultant = {d.key for d in documents_for("consultant")}
    partner = {d.key for d in documents_for("partner")}
    assert consultant == {
        "charte_informatique",
        "ar_charte_informatique",
        "engagement_confidentialite",
    }
    assert partner == {"charte_achats_responsables", "ar_charte_achats_responsables"}
    assert not consultant & partner


def test_legacy_result_keys_are_preserved():
    """L'API expose déjà ces clés : les renommer casserait les appelants."""
    by_key = {d.key: d.result_key for d in CHARTER_DOCUMENTS}
    assert by_key["ar_charte_informatique"] == "ar_s3_key"
    assert by_key["engagement_confidentialite"] == "engagement_s3_key"


def test_unknown_target_yields_no_document():
    assert documents_for("inconnu") == ()


# ── Chartes (multipages, unilatérales) ───────────────────────────────────────


def test_charte_informatique_renders_all_its_sections():
    _, text, pages = _render("charte_informatique.html")

    assert pages >= 3
    assert _has(text, "Charte informatique")
    assert _has(text, "Sécurité des systèmes d'information")
    # Les dix sections de la maquette, première et dernière comprises.
    assert _has(text, "1Champ d'application")
    assert _has(text, "10Entrée en vigueur et révision")
    # Sections propres à cette charte.
    assert _has(text, "Usage d'équipements personnels (BYOD)")
    assert _has(text, "intelligence artificielle générative")


def test_charte_achats_responsables_renders_all_its_sections():
    _, text, pages = _render("charte_achats_responsables.html")

    assert pages >= 3
    assert _has(text, "Charte des achats responsables et des partenaires")
    assert _has(text, "Préambule")
    assert _has(text, "1Objet de la charte")
    assert _has(text, "10Entrée en vigueur et évolution")
    assert _has(text, "loi Sapin II")
    assert _has(text, "alerte-ethique@leonum.fr")


@pytest.mark.parametrize(
    "template", ["charte_informatique.html", "charte_achats_responsables.html"]
)
def test_chartes_are_unilateral_documents(template):
    """Une charte n'est signée que par la Direction, sans signature électronique."""
    _, text, _ = _render(template)

    assert text.lower().count(_squash("Pour la Direction").lower()) == 1
    assert "yousign" not in text.lower()


@pytest.mark.parametrize(
    ("template", "mention"),
    [
        ("charte_informatique.html", "Confidentiel"),
        ("charte_achats_responsables.html", "Document interne"),
    ],
)
def test_charte_running_footer_carries_the_issuer_and_its_mention(template, mention):
    _, text, _ = _render(template)

    assert "LEONUM" in text
    assert _has(text, mention)


# ── Formulaires d'une page ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "template",
    [
        "ar_charte_informatique.html",
        "ar_charte_achats_responsables.html",
        "engagement_confidentialite.html",
    ],
)
def test_single_page_forms_fit_on_one_page(template):
    """Les formulaires de la maquette tiennent sur une page A4."""
    pdf, _, pages = _render(template)

    assert pdf.startswith(b"%PDF")
    assert pages == 1


def test_ar_charte_informatique_names_the_document_and_its_signer():
    _, text, _ = _render("ar_charte_informatique.html")

    assert _has(text, "Accusé de réception")
    assert _has(text, "Charte informatique — Version 2026.1")
    assert _has(text, "Identification du collaborateur")
    assert _has(text, "Karim BENALI")
    assert _has(text, "Le collaborateur")
    # Document signé : la mention Yousign est attendue, contrairement aux chartes.
    assert "yousign" in text.lower()


def test_ar_charte_achats_responsables_identifies_the_partner():
    _, text, _ = _render("ar_charte_achats_responsables.html")

    assert _has(text, "Charte des achats responsables et des partenaires — Version 2026.1")
    assert _has(text, "Identification du partenaire")
    # Les trois lignes d'identification propres au partenaire.
    assert _has(text, "Monsieur Karim BENALI")
    assert _has(text, "Président")
    assert _has(text, "AKEMA TECH")
    assert _has(text, "Le partenaire")


def test_engagement_confidentialite_carries_the_mission_and_the_five_year_term():
    _, text, _ = _render("engagement_confidentialite.html")

    assert _has(text, "Engagement de confidentialité")
    assert _has(text, "TMA Socle Data")
    assert _has(text, "cinq (5) ans")


def test_forms_render_without_optional_context():
    """Un contexte minimal ne doit ni lever ni laisser apparaître « None »."""
    pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")
    pymupdf = pytest.importorskip("pymupdf", reason="pymupdf absent de cet environnement")

    minimal = {"issuer_company_name": "LEONUM"}
    for document in CHARTER_DOCUMENTS:
        pdf = render_pdf(document.template, dict(minimal))
        text = "\n".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
        assert "None" not in text, document.key
