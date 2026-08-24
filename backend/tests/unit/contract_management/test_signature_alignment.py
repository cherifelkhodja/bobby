"""Alignement des blocs de signature des documents bilatéraux.

Les deux signataires n'ont pas la même identité : « SC HOLDING, elle-même
représentée par Madame Selma HIZEM » tient trois lignes là où le partenaire en
tient une. Sans précaution, la zone de signature de gauche descend plus bas que
celle de droite et le document paraît de travers. Ces tests mesurent les boîtes
réellement produites plutôt que la présence de classes CSS.
"""

import pytest

from app.contract_management.infrastructure.adapters.pdf_rendering import (
    TEMPLATE_DIR,
    apply_brand_theme,
    build_environment,
)


def _signature_zones(template_name: str, context: dict) -> list[tuple[float, float]]:
    """Positions (x, y) des zones de signature, dans l'ordre du document."""
    weasyprint = pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")
    apply_brand_theme(context)
    html = build_environment(TEMPLATE_DIR).get_template(template_name).render(**context)
    document = weasyprint.HTML(string=html, base_url=str(TEMPLATE_DIR)).render()

    def walk(box):
        yield box
        for child in getattr(box, "children", []):
            yield from walk(child)

    zones = []
    for page in document.pages:
        for box in walk(page._page_box):
            # La zone de signature est le seul bloc à bordure pointillée : on
            # la reconnaît à son style, pas à une classe.
            style = getattr(box, "style", None)
            if style is None or box.element_tag != "div":
                continue
            if style["border_top_style"] == "dashed" and box.height:
                zones.append((round(box.position_x, 1), round(box.position_y, 1)))
    return zones


class TestPurchaseOrder:
    """Bon de commande."""

    def test_both_signature_zones_start_at_the_same_height(self):
        from tests.unit.contract_management.test_purchase_order_document import (
            _company,
            _framework,
            _make_use_case,
            _purchase_order,
            _third_party,
        )

        purchase_order = _purchase_order()
        use_case, _ = _make_use_case(purchase_order)
        context = use_case._build_context(purchase_order, _third_party(), _framework(), _company())

        zones = _signature_zones("bon_de_commande.html", context)

        assert len(zones) == 2
        assert zones[0][1] == zones[1][1]
        assert zones[0][0] != zones[1][0]


class TestContract:
    """Contrat de sous-traitance."""

    def test_both_signature_zones_start_at_the_same_height(self):
        from app.contract_management.infrastructure.adapters.html_pdf_contract_generator import (
            TEMPLATE_NAME,
        )
        from tests.unit.contract_management.test_contract_template_rendering import _context

        zones = _signature_zones(TEMPLATE_NAME, _context())

        assert len(zones) == 2
        assert zones[0][1] == zones[1][1]
        assert zones[0][0] != zones[1][0]
