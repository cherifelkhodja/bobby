"""Sélection des fournisseurs du panel proposés à un bon de commande."""

from uuid import uuid4

from app.contract_management.application.panel_suppliers import (
    PanelSupplier,
    select_panel_suppliers,
)

GEMINI = uuid4()
CRAFTMANIA = uuid4()


def _supplier(**overrides) -> PanelSupplier:
    defaults = {
        "third_party_id": uuid4(),
        "company_name": "LEONUM",
        "third_party_type": "sous_traitant",
        "contract_request_id": uuid4(),
        "framework_reference": "GEM-CC-003",
        "framework_status": "active",
        "framework_company_id": GEMINI,
    }
    defaults.update(overrides)
    return PanelSupplier(**defaults)


class TestScope:
    """Le panel est celui de la société émettrice, pas celui du groupe."""

    def test_a_framework_of_another_company_does_not_open_the_panel(self):
        """Un cadre signé avec Gemini ne rend pas le fournisseur commandable par Craftmania."""
        suppliers = select_panel_suppliers([_supplier()], CRAFTMANIA)

        assert suppliers == []

    def test_the_framework_of_the_issuing_company_is_proposed(self):
        supplier = _supplier()

        assert select_panel_suppliers([supplier], GEMINI) == [supplier]

    def test_a_legacy_framework_without_company_stays_available(self):
        """Les dossiers antérieurs au multi-sociétés ne sont pas mis au rebut."""
        supplier = _supplier(framework_company_id=None)

        assert select_panel_suppliers([supplier], CRAFTMANIA) == [supplier]

    def test_without_an_issuing_company_the_whole_panel_is_proposed(self):
        """Un bon de commande dont l'émetteur reste à choisir ne filtre rien."""
        gemini = _supplier(company_name="LEONUM")
        craftmania = _supplier(company_name="ARTEMYS", framework_company_id=CRAFTMANIA)

        suppliers = select_panel_suppliers([gemini, craftmania], None)

        assert set(suppliers) == {gemini, craftmania}


class TestUsableFrameworks:
    """Tous les dossiers ne font pas entrer dans le panel."""

    def test_a_contractualisation_in_progress_is_enough_to_prepare_an_order(self):
        """Le bon de commande se prépare pendant la signature du cadre ; seul l'envoi attend."""
        supplier = _supplier(framework_status="collecting_documents")

        suppliers = select_panel_suppliers([supplier], GEMINI)

        assert suppliers == [supplier]
        assert suppliers[0].framework_signed is False

    def test_a_cancelled_framework_is_not_a_panel_entry(self):
        assert select_panel_suppliers([_supplier(framework_status="cancelled")], GEMINI) == []

    def test_a_payfit_redirection_is_not_a_panel_entry(self):
        """Un tiers renvoyé vers Payfit relève de la paie, pas de la sous-traitance."""
        supplier = _supplier(framework_status="redirected_payfit")

        assert select_panel_suppliers([supplier], GEMINI) == []

    def test_signed_statuses_are_recognised(self):
        for status in ("signed", "active", "archived"):
            assert _supplier(framework_status=status).framework_signed is True


class TestOnePerSupplier:
    """Un fournisseur n'apparaît qu'une fois, sous son meilleur dossier."""

    def test_the_signed_framework_wins_over_one_in_progress(self):
        third_party_id = uuid4()
        signed = _supplier(third_party_id=third_party_id, framework_reference="GEM-CC-003")
        in_progress = _supplier(
            third_party_id=third_party_id,
            framework_reference="PROV-2026-018",
            framework_status="configuring_contract",
        )

        suppliers = select_panel_suppliers([in_progress, signed], GEMINI)

        assert suppliers == [signed]

    def test_the_framework_of_the_issuing_company_wins_over_a_legacy_one(self):
        third_party_id = uuid4()
        legacy = _supplier(
            third_party_id=third_party_id,
            framework_reference="CC-2019-007",
            framework_company_id=None,
        )
        current = _supplier(third_party_id=third_party_id, framework_reference="GEM-CC-003")

        suppliers = select_panel_suppliers([legacy, current], GEMINI)

        assert suppliers == [current]


class TestOrdering:
    """L'ADV cherche par raison sociale."""

    def test_suppliers_are_sorted_by_company_name(self):
        first = _supplier(company_name="ARTEMYS")
        second = _supplier(company_name="leonum")
        third = _supplier(company_name="ZENIKA")

        suppliers = select_panel_suppliers([third, second, first], GEMINI)

        assert [s.company_name for s in suppliers] == ["ARTEMYS", "leonum", "ZENIKA"]

    def test_a_supplier_without_a_company_name_stays_listed(self):
        """Un dossier dont l'identité n'est pas encore saisie reste rattachable."""
        supplier = _supplier(company_name=None)

        assert select_panel_suppliers([supplier], GEMINI) == [supplier]


class TestLabel:
    """Le libellé de la liste ne peut pas être vide."""

    def test_the_company_name_is_used_when_it_exists(self):
        assert _supplier(company_name="LEONUM").label == "LEONUM"

    def test_the_signatory_names_a_supplier_without_a_company_name(self):
        """Un dossier ouvert par mail connaît son signataire avant sa raison sociale."""
        supplier = _supplier(
            company_name=None,
            signatory_first_name="Camille",
            signatory_last_name="Norel",
        )

        assert supplier.label == "Camille Norel"

    def test_the_contact_email_is_the_last_resort(self):
        supplier = _supplier(company_name="  ", contact_email="contact@leonum.fr")

        assert supplier.label == "contact@leonum.fr"
