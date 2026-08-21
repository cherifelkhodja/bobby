"""Tests de la génération du document de bon de commande."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.generate_purchase_order_document import (
    TEMPLATE_NAME,
    GeneratePurchaseOrderDocumentUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import PurchaseOrderIncompleteError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)
from app.contract_management.infrastructure.adapters.pdf_rendering import (
    apply_brand_theme,
    build_environment,
)

SALE_RATE = Decimal("780")


def _purchase_order(**overrides) -> PurchaseOrder:
    defaults = {
        "reference": "GEM-BC-001",
        "company_id": uuid4(),
        "third_party_id": uuid4(),
        "contract_request_id": uuid4(),
        "boond_positioning_id": 41,
        "boond_consultant_id": 4242,
        "consultant_civility": "M.",
        "consultant_first_name": "Camille",
        "consultant_last_name": "Norel",
        "consultant_email": "camille@akema.fr",
        "client_name": "Banque Régionale",
        "mission_title": "TMA Socle Data",
        "mission_description": "Reprise du socle de facturation",
        "mission_site_name": "Site de La Défense",
        "mission_postal_code": "92800",
        "mission_city": "Puteaux",
        "sale_daily_rate": SALE_RATE,
        "purchase_daily_rate": Decimal("500"),
        "days_sold": Decimal("20"),
        "free_days": Decimal("2"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _company():
    return SimpleNamespace(
        name="LEONUM",
        legal_form="SAS",
        capital="10000",
        head_office="54 avenue Hoche, 75008 Paris",
        rcs_city="Paris",
        rcs_number="842799959",
        representative_name="Mme Selma HIZEM",
        representative_quality="Présidente",
        signatory_name="Mme Selma HIZEM",
        color_code="#e95a6b",
        tva_number="FR23842799959",
        invoices_company_mail="factures@leonum.fr",
        logo_s3_key=None,
    )


def _third_party():
    return SimpleNamespace(
        company_name="AKEMA TECH",
        head_office_address="12 rue des Lilas, 69003 Lyon",
        siren="894213669",
        representative_civility="M.",
        representative_name="Karim BENALI",
        representative_title="Président",
        signatory_first_name="Karim",
        signatory_last_name="BENALI",
    )


def _framework():
    framework = ContractRequest(
        provisional_reference="PROV-2026-001",
        reference="GEM-CC-007",
        status=ContractRequestStatus.ACTIVE,
    )
    framework.status_history = [
        {"status": "signed", "entered_at": "2026-08-01T10:00:00"},
        {"status": "active", "entered_at": "2026-08-01T10:05:00"},
    ]
    framework.contract_config = {"payment_terms": "net_45_eom"}
    return framework


def _make_use_case(po, *, third_party=None, framework=None, company=None):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=po)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)

    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=framework)

    tp_repo = AsyncMock()
    tp_repo.get_by_id = AsyncMock(return_value=third_party)

    s3 = AsyncMock()
    s3.upload_file = AsyncMock()

    use_case = GeneratePurchaseOrderDocumentUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        s3_service=s3,
        db=None,
    )
    return use_case, s3


def _context(po=None) -> dict:
    """Contexte de gabarit produit par le use case, sans dépendance externe."""
    po = po or _purchase_order()
    use_case, _ = _make_use_case(po)
    return use_case._build_context(po, _third_party(), _framework(), _company())


class TestContext:
    """Contenu du contexte passé au gabarit."""

    def test_the_sale_rate_never_reaches_the_template(self):
        """Le TJM de vente est interne : il ne doit pas figurer au contexte."""
        context = _context()

        assert "sale_daily_rate" not in context
        assert str(SALE_RATE) not in " ".join(str(v) for v in context.values())

    def test_the_purchase_rate_and_amounts_are_present(self):
        """Le CJM, les jours et le total alimentent le document."""
        context = _context()

        assert context["purchase_daily_rate"] == "500"
        assert context["days_sold"] == "20"
        assert context["free_days"] == "2"
        assert context["billable_days"] == "18"
        assert context["total_amount"] == "9 000"

    def test_amounts_keep_their_cents_when_needed(self):
        """Un montant à décimales garde ses centimes."""
        po = _purchase_order(purchase_daily_rate=Decimal("512.50"), free_days=Decimal("0"))
        context = _context(po)

        assert context["purchase_daily_rate"] == "512,50"
        assert context["total_amount"] == "10 250"

    def test_half_days_are_rendered_with_a_comma(self):
        """Les demi-journées s'affichent à la française."""
        po = _purchase_order(days_sold=Decimal("20.50"), free_days=Decimal("0.50"))
        context = _context(po)

        assert context["days_sold"] == "20,5"
        assert context["billable_days"] == "20"

    def test_the_framework_contract_is_quoted(self):
        """Le bon de commande cite le cadre dont il dépend et sa date."""
        context = _context()

        assert context["framework_reference"] == "GEM-CC-007"
        assert context["framework_signed_date"] == "01/08/2026"
        assert context["payment_terms_label"] == "à 45 jours fin de mois"

    def test_mission_place_has_no_orphan_separator(self):
        """Un lieu partiellement renseigné ne produit pas de virgule esseulée."""
        po = _purchase_order(mission_site_name=None, mission_address=None)
        context = _context(po)

        assert context["mission_place"] == "92800 Puteaux"

    def test_parties_and_consultant_are_filled(self):
        context = _context()

        assert context["issuer_company_name"] == "LEONUM"
        assert context["partner_company_name"] == "AKEMA TECH"
        assert context["partner_signatory_name"] == "Karim BENALI"
        assert context["consultant_name"] == "Camille Norel"
        assert context["start_date"] == "01/09/2026"
        assert context["end_date"] == "28/02/2027"


class TestTemplateRendering:
    """Rendu du gabarit, sans dépendre de WeasyPrint."""

    def _html(self, po=None) -> str:
        context = _context(po)
        apply_brand_theme(context)
        return build_environment().get_template(TEMPLATE_NAME).render(**context)

    def test_the_template_renders(self):
        html = self._html()

        assert "Bon de commande" in html
        assert "GEM-BC-001" in html
        assert "TMA Socle Data" in html
        assert "AKEMA TECH" in html

    def test_the_sale_rate_is_absent_from_the_document(self):
        """Garde-fou de confidentialité au niveau du rendu."""
        assert str(SALE_RATE) not in self._html()

    def test_the_free_days_line_appears_only_when_there_are_any(self):
        with_free = self._html()
        without_free = self._html(_purchase_order(free_days=Decimal("0")))

        assert "gratuité" in with_free
        assert "gratuité" not in without_free

    def test_both_parties_have_a_signature_card(self):
        html = self._html()

        assert "Pour LEONUM" in html
        assert "Pour AKEMA TECH" in html
        assert "Bon pour accord" in html


class TestGeneration:
    """Effets de la génération."""

    @pytest.mark.asyncio
    async def test_incomplete_order_is_refused_before_any_upload(self):
        """Un bon de commande incomplet ne produit ni PDF ni fichier S3."""
        po = _purchase_order(third_party_id=None, purchase_daily_rate=None)
        use_case, s3 = _make_use_case(po)

        with pytest.raises(PurchaseOrderIncompleteError):
            await use_case.execute(po.id)

        s3.upload_file.assert_not_awaited()
        assert po.status == PurchaseOrderStatus.DRAFT

    @pytest.mark.asyncio
    async def test_generation_uploads_and_advances_the_status(self):
        pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")
        po = _purchase_order()
        use_case, s3 = _make_use_case(po, third_party=_third_party(), framework=_framework())

        result = await use_case.execute(po.id)

        s3.upload_file.assert_awaited_once()
        assert result.status == PurchaseOrderStatus.GENERATED
        assert result.s3_key_draft == "purchase-orders/GEM-BC-001/bon_de_commande_v1.pdf"

    @pytest.mark.asyncio
    async def test_regeneration_writes_a_new_version(self):
        pytest.importorskip("weasyprint", reason="WeasyPrint absent de cet environnement")
        po = _purchase_order()
        po.status_history = [
            {"status": "draft", "entered_at": "2026-08-01T10:00:00", "initial": True},
            {"status": "generated", "entered_at": "2026-08-02T10:00:00"},
            {"status": "draft", "entered_at": "2026-08-03T10:00:00"},
        ]
        use_case, _ = _make_use_case(po, third_party=_third_party(), framework=_framework())

        result = await use_case.execute(po.id)

        assert result.s3_key_draft.endswith("bon_de_commande_v2.pdf")
