"""Tests du rattachement manuel d'une prestation BoondManager à un bon de commande."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.attach_delivery_to_purchase_order import (
    AttachDeliveryToPurchaseOrderUseCase,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderDataError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _po(**overrides) -> PurchaseOrder:
    defaults = {
        "provisional_reference": "PROV-BC-2026-001",
        "reference": "GEM-BC-001",
        "status": PurchaseOrderStatus.SIGNED,
        "third_party_id": uuid4(),
        "boond_positioning_id": 538,
        "purchase_daily_rate": Decimal("585"),
        "days_sold": Decimal("124"),
        "free_days": Decimal("2"),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


# `None` étant une réponse à part entière — la prestation est illisible —, il
# faut un défaut qui ne s'y confonde pas.
_PRESTATION_LUE = {"id": 800, "title": "CHEBBI Rym", "resource_id": 2868}


def _make_use_case(po, *, delivery=_PRESTATION_LUE):
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=po)
    repo.save = AsyncMock(side_effect=lambda saved: saved)

    crm = AsyncMock()
    crm.get_delivery = AsyncMock(return_value=delivery)
    return AttachDeliveryToPurchaseOrderUseCase(repo, crm), crm, repo


class TestAttachDelivery:
    """Le recours de l'ADV quand le report n'a pas su retrouver la prestation."""

    @pytest.mark.asyncio
    async def test_the_delivery_is_remembered(self):
        po = _po()
        use_case, _, _ = _make_use_case(po)

        saved = await use_case.execute(po.id, 800)

        assert saved.boond_delivery_id == 800

    @pytest.mark.asyncio
    async def test_a_signed_order_still_accepts_it(self):
        """Le report a lieu après la signature : c'est là que le blocage se produit."""
        po = _po(status=PurchaseOrderStatus.SIGNED)
        use_case, _, _ = _make_use_case(po)

        saved = await use_case.execute(po.id, 800)

        assert saved.boond_delivery_id == 800
        assert saved.status == PurchaseOrderStatus.SIGNED

    @pytest.mark.asyncio
    async def test_the_blocking_warning_is_cleared(self):
        """Il annonçait la prestation manquante : la laisser afficherait un blocage levé."""
        po = _po()
        po.boond_sync_error = "Positionnement 538 passé à « Gagné », mais aucune prestation."
        use_case, _, _ = _make_use_case(po)

        saved = await use_case.execute(po.id, 800)

        assert saved.boond_sync_error is None

    @pytest.mark.asyncio
    async def test_the_delivery_is_read_back_before_being_kept(self):
        """Un numéro saisi de travers poserait l'achat sur la mission d'un autre."""
        po = _po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id, 800)

        crm.get_delivery.assert_awaited_once_with(800)

    @pytest.mark.asyncio
    async def test_an_unknown_delivery_is_refused(self):
        """Un achat mal rattaché ne se corrige qu'en le supprimant et le recréant."""
        po = _po()
        use_case, _, repo = _make_use_case(po, delivery=None)

        with pytest.raises(InvalidPurchaseOrderDataError):
            await use_case.execute(po.id, 999)

        assert po.boond_delivery_id is None
        repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_cancelled_order_is_refused(self):
        po = _po(status=PurchaseOrderStatus.CANCELLED)
        use_case, crm, _ = _make_use_case(po)

        with pytest.raises(InvalidPurchaseOrderDataError):
            await use_case.execute(po.id, 800)

        crm.get_delivery.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unknown_purchase_order_is_refused(self):
        use_case, _, repo = _make_use_case(_po())
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await use_case.execute(uuid4(), 800)
