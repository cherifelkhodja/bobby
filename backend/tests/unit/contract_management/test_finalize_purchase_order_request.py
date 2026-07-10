"""Tests for FinalizePurchaseOrderRequestUseCase.

Verrouille :
- pas de blocage sur la conformité (décision produit) : le BDC se finalise même
  si les documents du fournisseur ne sont pas à jour ;
- le montant envoyé à Boond est le TOTAL (TJM × nombre de jours).
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.finalize_purchase_order_request import (
    FinalizePurchaseOrderRequestUseCase,
)
from app.contract_management.domain.entities.purchase_order_request import (
    PurchaseOrderRequest,
)
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)


def _make_uc(*, compliance_status="compliant", quantity_sold=20):
    fc_id = uuid4()
    tp_id = uuid4()

    por = PurchaseOrderRequest(
        boond_positioning_id=433,
        commercial_email="com@example.com",
        reference="GEN-PO-001",
        framework_contract_id=fc_id,
        third_party_id=tp_id,
        boond_candidate_id=42,
        status=PurchaseOrderRequestStatus.CHECKING_COMPLIANCE,
        daily_rate=Decimal("500"),
        quantity_sold=quantity_sold,
    )

    por_repo = AsyncMock()
    por_repo.get_by_id = AsyncMock(return_value=por)
    por_repo.save = AsyncMock(side_effect=lambda x: x)

    fc = SimpleNamespace(id=fc_id, third_party_id=tp_id, reference="GEM-CC-0001", is_usable=True)
    fc_repo = AsyncMock()
    fc_repo.get_by_id = AsyncMock(return_value=fc)

    po_repo = AsyncMock()
    po_repo.get_by_contract_request_id = AsyncMock(return_value=None)
    po_repo.get_next_reference = AsyncMock(return_value="BDC-GEM-CC-0001-0001")
    po_repo.save = AsyncMock(side_effect=lambda x: x)

    tp = SimpleNamespace(id=tp_id, boond_provider_id=555, compliance_status=compliance_status)
    tp_repo = AsyncMock()
    tp_repo.get_by_id = AsyncMock(return_value=tp)

    crm = AsyncMock()
    crm.create_purchase_order = AsyncMock(return_value=9001)

    uc = FinalizePurchaseOrderRequestUseCase(
        purchase_order_request_repository=por_repo,
        framework_contract_repository=fc_repo,
        purchase_order_repository=po_repo,
        third_party_repository=tp_repo,
        crm_service=crm,
    )
    return uc, por, crm


class TestNoComplianceBlock:
    @pytest.mark.asyncio
    async def test_finalizes_even_with_stale_compliance(self):
        uc, por, crm = _make_uc(compliance_status="expired")

        po = await uc.execute(por.id)

        # Pas de blocage : le BDC est créé et actif
        assert po is not None
        assert por.status == PurchaseOrderRequestStatus.ACTIVE
        crm.create_purchase_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_po_has_no_contract_request_when_from_positioning(self):
        """Un BDC issu du positionnement (pas de CR d'origine) crée un PO avec
        contract_request_id=None (évite la FK violation vers cm_contract_requests)."""
        uc, por, _ = _make_uc()  # POR sans original_contract_request_id

        po = await uc.execute(por.id)

        assert po.contract_request_id is None


class TestBoondAmountIsTotal:
    @pytest.mark.asyncio
    async def test_amount_is_tjm_times_quantity(self):
        uc, por, crm = _make_uc(quantity_sold=20)

        await uc.execute(por.id)

        call = crm.create_purchase_order.call_args
        assert call.kwargs["amount"] == 500.0 * 20  # 10000.0

    @pytest.mark.asyncio
    async def test_amount_falls_back_to_tjm_without_quantity(self):
        uc, por, crm = _make_uc(quantity_sold=None)

        await uc.execute(por.id)

        call = crm.create_purchase_order.call_args
        assert call.kwargs["amount"] == 500.0
