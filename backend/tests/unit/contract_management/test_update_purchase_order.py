"""Tests for UpdatePurchaseOrderUseCase."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.update_purchase_order import (
    UpdatePurchaseOrderCommand,
    UpdatePurchaseOrderUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderDataError,
    PurchaseOrderNotEditableError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _make_po(**overrides) -> PurchaseOrder:
    defaults = {
        "provisional_reference": "PROV-BDC-2026-001",
        "reference": "GEM-BDC-001",
        "boond_positioning_id": 41,
        "days_sold": Decimal("20"),
        "purchase_daily_rate": Decimal("500"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _make_use_case(po, *, framework=None, other_requests=None, next_reference="GEM-BDC-002"):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=po)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)
    po_repo.get_next_reference = AsyncMock(return_value=next_reference)

    cr_repo = AsyncMock()
    cr_repo.get_framework_contract_for_third_party = AsyncMock(return_value=framework)
    cr_repo.list_by_third_party = AsyncMock(return_value=other_requests or [])
    cr_repo.get_company_code = AsyncMock(return_value="GCI")

    use_case = UpdatePurchaseOrderUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
    )
    return use_case, po_repo, cr_repo


def _command(po, **fields) -> UpdatePurchaseOrderCommand:
    return UpdatePurchaseOrderCommand(purchase_order_id=po.id, fields=fields)


class TestSupplierAttachment:
    """Rattachement du fournisseur et de son contrat cadre."""

    @pytest.mark.asyncio
    async def test_attaches_the_signed_framework_contract(self):
        """Le cadre signé du fournisseur devient le cadre du bon de commande."""
        company_id = uuid4()
        po = _make_po(company_id=company_id)
        framework = ContractRequest(
            provisional_reference="PROV-2026-001",
            status=ContractRequestStatus.ACTIVE,
            company_id=company_id,
        )
        use_case, _, cr_repo = _make_use_case(po, framework=framework)
        tp_id = uuid4()

        result = await use_case.execute(_command(po, third_party_id=tp_id))

        # La recherche est bornée à la société émettrice du bon de commande :
        # un cadre signé avec une autre société du groupe ne le couvre pas.
        cr_repo.get_framework_contract_for_third_party.assert_awaited_once_with(tp_id, company_id)
        assert result.third_party_id == tp_id
        assert result.contract_request_id == framework.id

    @pytest.mark.asyncio
    async def test_changing_the_issuing_company_reattaches_the_framework(self):
        """Changer de société émettrice peut rendre le rattachement caduc."""
        po = _make_po(company_id=uuid4(), third_party_id=uuid4())
        framework = ContractRequest(
            provisional_reference="PROV-2026-004",
            status=ContractRequestStatus.ACTIVE,
        )
        use_case, _, cr_repo = _make_use_case(po, framework=framework)
        new_company = uuid4()

        result = await use_case.execute(_command(po, company_id=new_company))

        cr_repo.get_framework_contract_for_third_party.assert_awaited_once_with(
            po.third_party_id, new_company
        )
        assert result.contract_request_id == framework.id

    @pytest.mark.asyncio
    async def test_a_dossier_of_another_company_is_not_attached(self):
        """Un dossier en cours chez une autre société ne sert pas de repli."""
        company_id = uuid4()
        po = _make_po(company_id=company_id)
        other_company_dossier = ContractRequest(
            provisional_reference="PROV-2026-005",
            status=ContractRequestStatus.COLLECTING_DOCUMENTS,
            company_id=uuid4(),
        )
        use_case, _, _ = _make_use_case(po, framework=None, other_requests=[other_company_dossier])

        result = await use_case.execute(_command(po, third_party_id=uuid4()))

        assert result.contract_request_id is None

    @pytest.mark.asyncio
    async def test_falls_back_to_the_dossier_in_progress(self):
        """Sans cadre signé, le dossier en cours est rattaché quand même."""
        company_id = uuid4()
        po = _make_po(company_id=company_id)
        in_progress = ContractRequest(
            provisional_reference="PROV-2026-002",
            status=ContractRequestStatus.COLLECTING_DOCUMENTS,
            company_id=company_id,
        )
        use_case, _, _ = _make_use_case(po, framework=None, other_requests=[in_progress])

        result = await use_case.execute(_command(po, third_party_id=uuid4()))

        assert result.contract_request_id == in_progress.id

    @pytest.mark.asyncio
    async def test_ignores_cancelled_dossiers(self):
        """Un dossier annulé ne sert pas de rattachement."""
        po = _make_po()
        cancelled = ContractRequest(
            provisional_reference="PROV-2026-003",
            status=ContractRequestStatus.CANCELLED,
        )
        use_case, _, _ = _make_use_case(po, framework=None, other_requests=[cancelled])

        result = await use_case.execute(_command(po, third_party_id=uuid4()))

        assert result.contract_request_id is None

    @pytest.mark.asyncio
    async def test_detaching_the_supplier_clears_the_framework(self):
        """Retirer le fournisseur détache aussi son cadre."""
        po = _make_po(third_party_id=uuid4(), contract_request_id=uuid4())
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(_command(po, third_party_id=None))

        assert result.third_party_id is None
        assert result.contract_request_id is None


class TestConsistencyChecks:
    """Cohérence des conditions saisies."""

    @pytest.mark.asyncio
    async def test_free_days_cannot_exceed_days_sold(self):
        po = _make_po()
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError, match="gratuité"):
            await use_case.execute(_command(po, free_days=Decimal("25")))

    @pytest.mark.asyncio
    async def test_days_sold_must_be_positive(self):
        po = _make_po()
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError, match="jours vendus"):
            await use_case.execute(_command(po, days_sold=Decimal("0")))

    @pytest.mark.asyncio
    async def test_rates_cannot_be_negative(self):
        po = _make_po()
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError, match="CJM"):
            await use_case.execute(_command(po, purchase_daily_rate=Decimal("-1")))

    @pytest.mark.asyncio
    async def test_end_date_cannot_precede_start_date(self):
        po = _make_po()
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError, match="date de fin"):
            await use_case.execute(_command(po, end_date=date(2026, 8, 1)))

    @pytest.mark.asyncio
    async def test_unknown_fields_are_refused(self):
        """Les champs hors mission ne se modifient pas par cette porte."""
        po = _make_po()
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError, match="boond_purchase_order_id"):
            await use_case.execute(_command(po, boond_purchase_order_id=99))


class TestDocumentFreshness:
    """Un document généré ne doit pas survivre à une modification de la mission."""

    @pytest.mark.asyncio
    async def test_editing_a_generated_order_sends_it_back_to_draft(self):
        po = _make_po(
            third_party_id=uuid4(),
            company_id=uuid4(),
            client_name="Client",
            mission_title="Mission",
            status=PurchaseOrderStatus.GENERATED,
            s3_key_draft="contracts/bdc/draft.pdf",
        )
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(_command(po, purchase_daily_rate=Decimal("520")))

        assert result.status == PurchaseOrderStatus.DRAFT
        assert result.s3_key_draft is None

    @pytest.mark.asyncio
    async def test_internal_only_changes_keep_the_document(self):
        """Le TJM de vente n'est pas imprimé : le document reste valable."""
        po = _make_po(status=PurchaseOrderStatus.GENERATED, s3_key_draft="contracts/bdc/draft.pdf")
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(_command(po, sale_daily_rate=Decimal("700")))

        assert result.status == PurchaseOrderStatus.GENERATED
        assert result.s3_key_draft == "contracts/bdc/draft.pdf"

    @pytest.mark.asyncio
    async def test_a_sent_order_is_no_longer_editable(self):
        po = _make_po(status=PurchaseOrderStatus.SENT_FOR_SIGNATURE)
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderNotEditableError):
            await use_case.execute(_command(po, client_name="Autre client"))


class TestReferenceNumbering:
    """Le numéro définitif n'est pris qu'à la génération, et suit la société."""

    @pytest.mark.asyncio
    async def test_a_draft_is_not_numbered_when_it_is_completed(self):
        """Compléter un brouillon ne consomme pas de numéro définitif."""
        po = _make_po(company_id=uuid4(), reference=None)
        use_case, po_repo, cr_repo = _make_use_case(po)

        result = await use_case.execute(_command(po, company_id=uuid4()))

        po_repo.get_next_reference.assert_not_awaited()
        cr_repo.get_company_code.assert_not_awaited()
        assert result.reference is None
        assert result.display_reference == "PROV-BDC-2026-001"

    @pytest.mark.asyncio
    async def test_changing_the_issuing_company_releases_the_definitive_reference(self):
        """Un numéro Gemini ne peut pas suivre le bon dans la séquence d'une autre société."""
        po = _make_po(company_id=uuid4())
        use_case, po_repo, _ = _make_use_case(po)

        result = await use_case.execute(_command(po, company_id=uuid4()))

        # Aucun numéro n'est pris ici : la nouvelle séquence sera servie à la
        # prochaine génération du document.
        po_repo.get_next_reference.assert_not_awaited()
        assert result.reference is None
        assert result.display_reference == "PROV-BDC-2026-001"

    @pytest.mark.asyncio
    async def test_the_reference_is_kept_when_the_company_does_not_change(self):
        """Corriger la mission ne renumérote pas un bon déjà généré."""
        company_id = uuid4()
        po = _make_po(company_id=company_id)
        use_case, po_repo, _ = _make_use_case(po)

        result = await use_case.execute(_command(po, company_id=company_id, client_name="ACME"))

        po_repo.get_next_reference.assert_not_awaited()
        assert result.reference == "GEM-BDC-001"


class TestMissingOrder:
    """Bon de commande introuvable."""

    @pytest.mark.asyncio
    async def test_unknown_purchase_order_is_reported(self):
        use_case, po_repo, _ = _make_use_case(None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await use_case.execute(
                UpdatePurchaseOrderCommand(purchase_order_id=uuid4(), fields={"client_name": "X"})
            )
