"""Tests de la synchronisation BoondManager d'un bon de commande signé."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.sync_purchase_order_to_boond import (
    SyncPurchaseOrderToBoondUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import PurchaseOrderBoondSyncError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _signed_po(**overrides) -> PurchaseOrder:
    defaults = {
        "reference": "GEM-BC-001",
        "status": PurchaseOrderStatus.SIGNED,
        "third_party_id": uuid4(),
        "contract_request_id": uuid4(),
        "boond_positioning_id": 41,
        "boond_consultant_id": 4242,
        "boond_consultant_type": "candidate",
        "purchase_daily_rate": Decimal("500"),
        "days_sold": Decimal("20"),
        "free_days": Decimal("2"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _make_use_case(po, *, provider_id=777, third_party_type="sous_traitant"):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=po)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)

    framework = ContractRequest(
        provisional_reference="PROV-2026-001",
        status=ContractRequestStatus.ACTIVE,
        third_party_type=third_party_type,
    )
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=framework)

    tp_repo = AsyncMock()
    tp_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(boond_provider_id=provider_id, company_name="AKEMA TECH")
        if provider_id
        else SimpleNamespace(boond_provider_id=None, company_name="AKEMA TECH")
    )

    crm = AsyncMock()
    crm.resolve_resource_id = AsyncMock(return_value=None)
    crm.convert_candidate_to_resource = AsyncMock(return_value=9001)
    crm.update_resource_administrative = AsyncMock()
    crm.create_boond_contract = AsyncMock(return_value=555)
    crm.create_purchase_order = AsyncMock(return_value=666)
    crm.renew_delivery = AsyncMock(return_value={"id": 798, "purchase_id": 900, "contract_id": 264})
    crm.update_delivery = AsyncMock()

    use_case = SyncPurchaseOrderToBoondUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        crm_service=crm,
        db=None,
    )
    return use_case, crm, po_repo


class TestPrerequisites:
    """Ce qu'il faut avant de pouvoir pousser dans Boond."""

    @pytest.mark.asyncio
    async def test_an_unsigned_order_is_refused(self):
        po = _signed_po(status=PurchaseOrderStatus.GENERATED)
        use_case, crm, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderBoondSyncError, match="signé"):
            await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_supplier_absent_from_boond_is_refused(self):
        """La société fournisseur naît à la signature du contrat cadre."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po, provider_id=None)

        with pytest.raises(PurchaseOrderBoondSyncError, match="société fournisseur"):
            await use_case.execute(po.id)

        crm.create_purchase_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_order_without_positioning_is_refused(self):
        po = _signed_po(boond_positioning_id=None)
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderBoondSyncError, match="positionnement"):
            await use_case.execute(po.id)


class TestResourceResolution:
    """Le consultant doit être une ressource Boond."""

    @pytest.mark.asyncio
    async def test_a_candidate_is_converted(self):
        """Le bon de commande acte la mission : le candidat devient ressource."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_awaited_once_with(4242, state=3)
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 9001

    @pytest.mark.asyncio
    async def test_an_existing_resource_is_reused(self):
        """Un candidat déjà converti n'est pas converti une seconde fois."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.resolve_resource_id = AsyncMock(return_value=8500)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_not_awaited()
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 8500

    @pytest.mark.asyncio
    async def test_a_resource_consultant_is_used_as_is(self):
        po = _signed_po(boond_consultant_type="resource", boond_consultant_id=8888)
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.resolve_resource_id.assert_not_awaited()
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 8888

    @pytest.mark.asyncio
    async def test_a_failed_provider_link_does_not_stop_the_sync(self):
        """Le rattachement administratif est corrigeable à la main dans Boond."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.update_resource_administrative = AsyncMock(side_effect=RuntimeError("Boond 422"))

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        crm.create_purchase_order.assert_awaited_once()


class TestBoondWrites:
    """Contenu des écritures Boond."""

    @pytest.mark.asyncio
    async def test_the_contract_carries_the_purchase_rate_and_dates(self):
        """Le contrat Boond porte le CJM d'achat, jamais le TJM de vente."""
        po = _signed_po(sale_daily_rate=Decimal("780"))
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.create_boond_contract.await_args.kwargs
        assert kwargs["daily_rate"] == 500.0
        assert kwargs["type_of"] == 2  # sous-traitant
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"

    @pytest.mark.asyncio
    async def test_the_contract_type_follows_the_third_party_type(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po, third_party_type="portage_salarial")

        await use_case.execute(po.id)

        assert crm.create_boond_contract.await_args.kwargs["type_of"] == 6

    @pytest.mark.asyncio
    async def test_the_purchase_order_carries_the_billable_total(self):
        """Montant Boond = (jours vendus - gratuité) x CJM."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.create_purchase_order.await_args.kwargs
        assert kwargs["amount"] == 9000.0  # 18 x 500
        assert kwargs["reference"] == "GEM-BC-001"
        assert kwargs["positioning_id"] == 41

    @pytest.mark.asyncio
    async def test_the_order_becomes_active(self):
        po = _signed_po()
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        assert result.boond_contract_id == 555
        assert result.boond_purchase_order_id == 666
        assert result.boond_sync_error is None


class TestIdempotence:
    """Relancer une synchronisation ne duplique rien."""

    @pytest.mark.asyncio
    async def test_existing_boond_objects_are_not_recreated(self):
        po = _signed_po(
            status=PurchaseOrderStatus.ACTIVE,
            boond_contract_id=555,
            boond_purchase_order_id=666,
            boond_sync_error="Boond HTTP 500",
        )
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        crm.create_purchase_order.assert_not_awaited()
        assert result.boond_sync_error is None

    @pytest.mark.asyncio
    async def test_a_partial_sync_only_completes_what_is_missing(self):
        """Le contrat existe déjà, seul le bon de commande reste à créer."""
        po = _signed_po(boond_contract_id=555)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        crm.create_purchase_order.assert_awaited_once()
        assert result.boond_purchase_order_id == 666


class TestRenewals:
    """Une reconduction ne superpose pas un second contrat Boond."""

    @pytest.mark.asyncio
    async def test_a_renewal_uses_the_native_delivery_renewal(self):
        """Boond sait renouveler une prestation : on passe par là."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.renew_delivery.assert_awaited_once_with(797)
        assert result.boond_delivery_id == 798
        # L'achat créé par Boond est repris tel quel, sans en créer un second.
        crm.create_purchase_order.assert_not_awaited()
        assert result.boond_purchase_order_id == 900

    @pytest.mark.asyncio
    async def test_the_renewed_delivery_is_realigned_on_the_new_period(self):
        """Boond duplique à l'identique : sans recalage, les dates seraient fausses."""
        po = _signed_po(
            parent_purchase_order_id=uuid4(),
            boond_delivery_id=797,
            sale_daily_rate=Decimal("780"),
        )
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.update_delivery.await_args.kwargs
        assert kwargs["delivery_id"] == 798
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"
        assert kwargs["days_sold"] == 20.0
        assert kwargs["free_days"] == 2.0
        assert kwargs["purchase_daily_rate"] == 500.0
        assert kwargs["sale_daily_rate"] == 780.0

    @pytest.mark.asyncio
    async def test_a_renewal_without_purchase_falls_back_to_creating_one(self):
        """Si Boond n'a pas produit l'achat, on le crée par la voie habituelle."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.renew_delivery = AsyncMock(return_value={"id": 798, "purchase_id": None})

        result = await use_case.execute(po.id)

        crm.create_purchase_order.assert_awaited_once()
        assert result.boond_purchase_order_id == 666

    @pytest.mark.asyncio
    async def test_a_failed_realignment_warns_without_failing_the_sync(self):
        """La prestation et l'achat existent : l'échec du recalage n'invalide rien."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.update_delivery = AsyncMock(side_effect=RuntimeError("Boond 405"))

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        assert "recaler dans BoondManager" in result.boond_sync_error
        assert "798" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_an_empty_renewal_response_is_an_error(self):
        """Sans prestation en retour, il n'y a rien à rattacher."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.renew_delivery = AsyncMock(return_value=None)

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        crm.create_purchase_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_renewal_without_a_delivery_creates_a_plain_purchase_order(self):
        """Sans prestation connue, la reconduction retombe sur le chemin standard."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.renew_delivery.assert_not_awaited()
        crm.create_purchase_order.assert_awaited_once()
        assert result.boond_purchase_order_id == 666

    @pytest.mark.asyncio
    async def test_a_renewal_does_not_create_a_second_contract(self):
        """Le consultant reste sous le même contrat de sous-traitance."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        assert result.boond_contract_id is None

    @pytest.mark.asyncio
    async def test_a_renewal_still_creates_its_own_purchase_order(self):
        """Chaque période est un engagement d'achat distinct."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_purchase_order.assert_awaited_once()
        assert result.boond_purchase_order_id == 666
        assert result.status == PurchaseOrderStatus.ACTIVE


class TestErrorReporting:
    """Une erreur Boond doit rester lisible et rejouable."""

    @pytest.mark.asyncio
    async def test_the_error_is_stored_on_the_order(self):
        po = _signed_po()
        use_case, crm, po_repo = _make_use_case(po)
        crm.create_boond_contract = AsyncMock(side_effect=RuntimeError("Boond 422 unprocessable"))

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        assert "422" in po.boond_sync_error
        assert po.status == PurchaseOrderStatus.SIGNED
        po_repo.save.assert_awaited()

    @pytest.mark.asyncio
    async def test_an_http_response_is_summarised(self):
        """Le corps de la réponse Boond est repris, tronqué."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        class _BoondHttpError(Exception):
            """Erreur porteuse d'une réponse HTTP, comme celles de httpx."""

            response = SimpleNamespace(status_code=422, text="quantity is required")

        failure = RuntimeError("wrapped")
        failure.__cause__ = _BoondHttpError()
        crm.create_purchase_order = AsyncMock(side_effect=failure)

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        assert po.boond_sync_error == "Boond HTTP 422: quantity is required"
