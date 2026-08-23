"""Tests for the PurchaseOrder entity and its state machine."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    FrameworkContractNotSignedError,
    InvalidPurchaseOrderStatusError,
    PurchaseOrderIncompleteError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _complete_po(**overrides) -> PurchaseOrder:
    """A purchase order with everything needed to be generated."""
    defaults = {
        "provisional_reference": "PROV-BC-2026-001",
        "reference": "GEM-BC-001",
        "company_id": uuid4(),
        "third_party_id": uuid4(),
        "contract_request_id": uuid4(),
        "boond_consultant_id": 4242,
        "boond_consultant_type": "resource",
        "consultant_first_name": "Camille",
        "consultant_last_name": "Norel",
        "boond_positioning_id": 41,
        "client_name": "Client final",
        "mission_title": "Développeur backend",
        "sale_daily_rate": Decimal("650"),
        "purchase_daily_rate": Decimal("500"),
        "days_sold": Decimal("20"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


class TestAmounts:
    """Montants : jours facturables, total, marge."""

    def test_total_amount_excludes_free_days(self):
        """Les jours de gratuité sortent du montant facturé."""
        po = _complete_po(days_sold=Decimal("20"), free_days=Decimal("2"))
        assert po.billable_days == Decimal("18")
        assert po.total_amount == Decimal("9000")  # 18 x 500

    def test_total_amount_without_free_days(self):
        """Sans gratuité, le montant est jours vendus x CJM."""
        po = _complete_po(days_sold=Decimal("20"))
        assert po.total_amount == Decimal("10000")

    def test_half_days_are_supported(self):
        """Les demi-journées sont représentables (Numeric(6, 2))."""
        po = _complete_po(days_sold=Decimal("20.5"), free_days=Decimal("0.5"))
        assert po.billable_days == Decimal("20.0")
        assert po.total_amount == Decimal("10000.0")

    def test_billable_days_never_negative(self):
        """Une gratuité supérieure aux jours vendus ne produit pas un négatif."""
        po = _complete_po(days_sold=Decimal("5"), free_days=Decimal("8"))
        assert po.billable_days == Decimal("0")
        assert po.total_amount == Decimal("0")

    def test_margin_uses_sale_rate(self):
        """La marge indicative s'appuie sur le TJM de vente."""
        po = _complete_po(days_sold=Decimal("20"), free_days=Decimal("2"))
        assert po.estimated_margin == Decimal("2700")  # (650 - 500) x 18

    def test_margin_is_none_without_sale_rate(self):
        """Sans TJM de vente renseigné, pas de marge calculable."""
        po = _complete_po(sale_daily_rate=None)
        assert po.estimated_margin is None

    def test_amounts_are_zero_when_mission_is_empty(self):
        """Un BDC tout juste créé par webhook n'a pas encore de montant."""
        po = PurchaseOrder(provisional_reference="PROV-BC-2026-002")
        assert po.billable_days == Decimal("0")
        assert po.total_amount == Decimal("0")


class TestCompleteness:
    """Complétude avant génération."""

    def test_webhook_created_order_needs_a_third_party(self):
        """Un BDC né du webhook est « à rattacher »."""
        po = PurchaseOrder(provisional_reference="PROV-BC-2026-002", boond_positioning_id=41)
        assert po.needs_third_party
        assert not po.is_complete
        assert "le fournisseur" in po.missing_fields

    def test_complete_order_reports_no_missing_field(self):
        """Un BDC complet ne liste aucun manque."""
        po = _complete_po()
        assert po.is_complete
        assert po.missing_fields == []
        assert not po.needs_third_party

    def test_missing_fields_are_listed_in_french(self):
        """Les manques sont listés pour affichage à l'ADV."""
        po = _complete_po(purchase_daily_rate=None, end_date=None)
        assert po.missing_fields == [
            "le CJM (coût journalier d'achat)",
            "la date de fin",
        ]

    def test_zero_rate_is_not_treated_as_missing(self):
        """Un CJM à 0 est une valeur saisie, pas un champ manquant."""
        po = _complete_po(purchase_daily_rate=Decimal("0"))
        assert po.is_complete


class TestLifecycle:
    """Parcours du bon de commande."""

    def test_generation_requires_completeness(self):
        """Générer un BDC incomplet est refusé."""
        po = PurchaseOrder(provisional_reference="PROV-BC-2026-002", boond_positioning_id=41)
        with pytest.raises(PurchaseOrderIncompleteError) as exc:
            po.mark_generated("contracts/bdc/draft.pdf")
        assert "le fournisseur" in str(exc.value)
        assert po.status == PurchaseOrderStatus.DRAFT

    def test_generation_stores_the_document(self):
        """La génération enregistre le brouillon et fait avancer le statut."""
        po = _complete_po()
        po.mark_generated("contracts/bdc/draft.pdf")
        assert po.status == PurchaseOrderStatus.GENERATED
        assert po.s3_key_draft == "contracts/bdc/draft.pdf"

    def test_cannot_send_before_framework_contract_is_signed(self):
        """L'envoi en signature attend la signature du contrat cadre."""
        po = _complete_po()
        po.mark_generated("contracts/bdc/draft.pdf")
        with pytest.raises(FrameworkContractNotSignedError):
            po.send_for_signature(framework_contract_signed=False)
        assert po.status == PurchaseOrderStatus.GENERATED
        assert po.sent_for_signature_at is None

    def test_full_happy_path(self):
        """Brouillon → généré → envoyé → signé → actif → clôturé."""
        po = _complete_po()
        po.mark_generated("contracts/bdc/draft.pdf")
        po.send_for_signature(framework_contract_signed=True)
        assert po.sent_for_signature_at is not None
        po.mark_signed("contracts/bdc/signed.pdf")
        assert po.signed_at is not None
        po.mark_active()
        po.close()
        assert po.status == PurchaseOrderStatus.CLOSED
        assert [h["status"] for h in po.status_history] == [
            "draft",
            "generated",
            "sent_for_signature",
            "signed",
            "active",
            "closed",
        ]

    def test_sync_error_is_cleared_when_activated(self):
        """Passer actif efface l'erreur de synchronisation précédente."""
        po = _complete_po()
        po.mark_generated("d.pdf")
        po.send_for_signature(framework_contract_signed=True)
        po.mark_signed("s.pdf")
        po.boond_sync_error = "Boond HTTP 422"
        po.mark_active()
        assert po.boond_sync_error is None

    def test_signed_order_cannot_be_cancelled(self):
        """Un BDC signé n'est plus annulable."""
        po = _complete_po()
        po.mark_generated("d.pdf")
        po.send_for_signature(framework_contract_signed=True)
        po.mark_signed("s.pdf")
        with pytest.raises(InvalidPurchaseOrderStatusError):
            po.cancel()

    def test_draft_can_be_cancelled(self):
        """Un brouillon s'annule."""
        po = _complete_po()
        po.cancel()
        assert po.status == PurchaseOrderStatus.CANCELLED

    def test_generated_order_returns_to_draft_when_edited(self):
        """Modifier la mission d'un BDC généré le ramène en brouillon."""
        po = _complete_po()
        po.mark_generated("d.pdf")
        po.transition_to(PurchaseOrderStatus.DRAFT)
        assert po.status == PurchaseOrderStatus.DRAFT

    def test_sent_order_can_be_corrected_and_resent(self):
        """Un BDC envoyé mais non signé peut être corrigé puis renvoyé."""
        po = _complete_po()
        po.mark_generated("d.pdf")
        po.send_for_signature(framework_contract_signed=True)
        po.transition_to(PurchaseOrderStatus.GENERATED)
        po.send_for_signature(framework_contract_signed=True)
        assert po.status == PurchaseOrderStatus.SENT_FOR_SIGNATURE


class TestStatusValueObject:
    """Propriétés du value object de statut."""

    @pytest.mark.parametrize(
        ("status", "editable"),
        [
            (PurchaseOrderStatus.DRAFT, True),
            (PurchaseOrderStatus.GENERATED, True),
            (PurchaseOrderStatus.SENT_FOR_SIGNATURE, False),
            (PurchaseOrderStatus.SIGNED, False),
            (PurchaseOrderStatus.ACTIVE, False),
        ],
    )
    def test_editability(self, status, editable):
        """La mission n'est modifiable qu'avant l'envoi en signature."""
        assert status.is_editable is editable

    def test_terminal_statuses(self):
        """Clôturé et annulé sont terminaux."""
        assert PurchaseOrderStatus.CLOSED.is_final
        assert PurchaseOrderStatus.CANCELLED.is_final
        assert not PurchaseOrderStatus.ACTIVE.is_final
        assert PurchaseOrderStatus.CLOSED.allowed_transitions == frozenset()

    def test_every_status_has_a_french_label(self):
        """Chaque statut est affichable en français."""
        for status in PurchaseOrderStatus:
            assert status.display_name != status.value
