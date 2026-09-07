"""Tests for RenewPurchaseOrderUseCase."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.renew_purchase_order import (
    RenewPurchaseOrderCommand,
    RenewPurchaseOrderUseCase,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderDataError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _source(**overrides) -> PurchaseOrder:
    defaults = {
        "provisional_reference": "PROV-BDC-2026-001",
        "reference": "GEM-BDC-001",
        "status": PurchaseOrderStatus.ACTIVE,
        "company_id": uuid4(),
        "third_party_id": uuid4(),
        "contract_request_id": uuid4(),
        "boond_consultant_id": 4242,
        "boond_consultant_type": "resource",
        "consultant_first_name": "Camille",
        "consultant_last_name": "Norel",
        "boond_positioning_id": 41,
        "boond_need_id": 88,
        "boond_delivery_id": 41,
        "client_name": "Banque Régionale",
        "mission_title": "TMA Socle Data",
        "purchase_daily_rate": Decimal("500"),
        "sale_daily_rate": Decimal("780"),
        "days_sold": Decimal("20"),
        "free_days": Decimal("2"),
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 8, 31),
        "boond_contract_id": 555,
        "boond_purchase_order_id": 666,
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _make_use_case(source, next_reference="GEM-BDC-002"):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=source)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)
    po_repo.get_next_provisional_reference = AsyncMock(return_value="PROV-BDC-2026-002")
    po_repo.get_next_reference = AsyncMock(return_value=next_reference)

    cr_repo = AsyncMock()
    cr_repo.get_company_code = AsyncMock(return_value="GEM")

    use_case = RenewPurchaseOrderUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
    )
    return use_case, po_repo


def _command(source, **overrides) -> RenewPurchaseOrderCommand:
    defaults = {
        "purchase_order_id": source.id,
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return RenewPurchaseOrderCommand(**defaults)


class TestRenewal:
    """Une reconduction est un nouveau document, pas une prolongation en place."""

    @pytest.mark.asyncio
    async def test_the_renewal_is_a_new_draft_linked_to_its_parent(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(_command(source))

        assert renewal.id != source.id
        assert renewal.provisional_reference == "PROV-BDC-2026-002"
        assert renewal.reference is None
        assert renewal.status == PurchaseOrderStatus.DRAFT
        assert renewal.parent_purchase_order_id == source.id
        assert source.status == PurchaseOrderStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_mission_and_supplier_are_inherited(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(_command(source))

        assert renewal.third_party_id == source.third_party_id
        assert renewal.contract_request_id == source.contract_request_id
        assert renewal.boond_consultant_id == 4242
        assert renewal.client_name == "Banque Régionale"
        assert renewal.mission_title == "TMA Socle Data"

    @pytest.mark.asyncio
    async def test_the_boond_positioning_is_kept(self):
        """La mission ne change pas de nature : pas de second positionnement."""
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(_command(source))

        assert renewal.boond_positioning_id == 41
        assert renewal.boond_delivery_id == 41
        # Les objets Boond du bon de commande précédent ne sont pas repris :
        # la reconduction produira les siens.
        assert renewal.boond_contract_id is None
        assert renewal.boond_purchase_order_id is None

    @pytest.mark.asyncio
    async def test_conditions_are_carried_over_by_default(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(_command(source))

        assert renewal.purchase_daily_rate == Decimal("500")
        assert renewal.sale_daily_rate == Decimal("780")
        assert renewal.days_sold == Decimal("20")
        # La gratuité, elle, ne se reconduit pas d'elle-même.
        assert renewal.free_days == Decimal("0")

    @pytest.mark.asyncio
    async def test_conditions_can_be_revised(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(
            _command(
                source,
                days_sold=Decimal("30"),
                free_days=Decimal("1"),
                purchase_daily_rate=Decimal("520"),
            )
        )

        assert renewal.days_sold == Decimal("30")
        assert renewal.free_days == Decimal("1")
        assert renewal.purchase_daily_rate == Decimal("520")
        assert renewal.total_amount == Decimal("15080")  # 29 x 520

    @pytest.mark.asyncio
    async def test_the_new_period_is_applied(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        renewal = await use_case.execute(_command(source))

        assert renewal.start_date == date(2026, 9, 1)
        assert renewal.end_date == date(2027, 2, 28)


class TestGuards:
    """Ce qui empêche une reconduction."""

    @pytest.mark.asyncio
    async def test_a_draft_cannot_be_renewed(self):
        """Un bon de commande en préparation se corrige, il ne se reconduit pas."""
        source = _source(status=PurchaseOrderStatus.DRAFT)
        use_case, po_repo = _make_use_case(source)

        with pytest.raises(InvalidPurchaseOrderDataError, match="reconductible"):
            await use_case.execute(_command(source))

        po_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_cancelled_order_cannot_be_renewed(self):
        source = _source(status=PurchaseOrderStatus.CANCELLED)
        use_case, _ = _make_use_case(source)

        with pytest.raises(InvalidPurchaseOrderDataError):
            await use_case.execute(_command(source))

    @pytest.mark.asyncio
    async def test_an_inverted_period_is_refused(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        with pytest.raises(InvalidPurchaseOrderDataError, match="date de fin"):
            await use_case.execute(
                _command(source, start_date=date(2027, 1, 1), end_date=date(2026, 12, 1))
            )

    @pytest.mark.asyncio
    async def test_free_days_cannot_exceed_days_sold(self):
        source = _source()
        use_case, _ = _make_use_case(source)

        with pytest.raises(InvalidPurchaseOrderDataError, match="gratuité"):
            await use_case.execute(_command(source, days_sold=Decimal("5"), free_days=Decimal("6")))

    @pytest.mark.asyncio
    async def test_an_unknown_order_is_reported(self):
        use_case, _ = _make_use_case(None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await use_case.execute(
                RenewPurchaseOrderCommand(
                    purchase_order_id=uuid4(),
                    start_date=date(2026, 9, 1),
                    end_date=date(2027, 2, 28),
                )
            )
