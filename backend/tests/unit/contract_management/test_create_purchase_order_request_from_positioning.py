"""Tests for CreatePurchaseOrderRequestFromPositioningUseCase.

Verrouille :
- filtrage sur l'état 7 uniquement ;
- BDC créé ÉDITABLE quand le consultant est une ressource rattachée à un
  contrat cadre actif ;
- BDC créé VERROUILLÉ (PENDING_FRAMEWORK_CONTRACT) sinon (candidat, ou pas de
  contrat cadre) ;
- idempotence : un BDC existant pour le positionnement est renvoyé sans doublon.
"""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.create_purchase_order_request_from_positioning import (  # noqa: E501
    CreatePurchaseOrderRequestFromPositioningUseCase,
)
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)


def _webhook_payload(positioning_id: int = 433, new_state: int = 7) -> list:
    """Build a Boond positioning-update webhook payload (state change)."""
    return [
        {
            "data": {
                "id": "3_abc",
                "type": "webhookevent",
                "relationships": {"dependsOn": {"id": str(positioning_id), "type": "positioning"}},
                "included": [
                    {
                        "id": "117497",
                        "type": "log",
                        "attributes": {"content": {"diff": {"state": {"old": 0, "new": new_state}}}},
                    }
                ],
            }
        }
    ]


def _make_use_case(
    *,
    consultant_type: str = "resource",
    provider_company_id: int | None = 555,
    tp=None,
    fc=None,
    existing_por=None,
) -> CreatePurchaseOrderRequestFromPositioningUseCase:
    por_repo = AsyncMock()
    por_repo.get_by_positioning_id = AsyncMock(return_value=existing_por)
    por_repo.get_next_reference = AsyncMock(return_value="GEN-PO-001")
    por_repo.save = AsyncMock(side_effect=lambda x: x)

    cr_repo = AsyncMock()
    cr_repo.get_company_by_boond_agency_id = AsyncMock(return_value=None)
    cr_repo.get_company_code = AsyncMock(return_value="GEN")

    webhook_repo = AsyncMock()
    webhook_repo.exists = AsyncMock(return_value=False)
    webhook_repo.save = AsyncMock()

    tp_repo = AsyncMock()
    tp_repo.get_by_boond_provider_id = AsyncMock(return_value=tp)

    fc_repo = AsyncMock()
    fc_repo.get_active_by_third_party = AsyncMock(return_value=fc)

    crm = AsyncMock()
    crm.get_positioning = AsyncMock(
        return_value={
            "id": 433,
            "candidate_id": 42,
            "consultant_type": consultant_type,
            "need_id": 99,
            "daily_rate": "500",
            "quantity": 20,
            "start_date": "2026-08-01",
            "end_date": None,
            "consultant_first_name": "Jean",
            "consultant_last_name": "Dupont",
        }
    )
    crm.get_need = AsyncMock(
        return_value={"title": "Mission X", "client_name": "ACME", "agency_id": None, "manager_id": None,
                      "commercial_email": "com@example.com"}
    )
    crm.get_resource_provider_company_id = AsyncMock(return_value=provider_company_id)

    return CreatePurchaseOrderRequestFromPositioningUseCase(
        purchase_order_request_repository=por_repo,
        contract_request_repository=cr_repo,
        webhook_event_repository=webhook_repo,
        third_party_repository=tp_repo,
        framework_contract_repository=fc_repo,
        crm_service=crm,
        email_service=AsyncMock(),
        user_repository=None,
        frontend_url="http://front",
    )


class TestStateFilter:
    @pytest.mark.asyncio
    async def test_ignores_non_state_7(self):
        uc = _make_use_case()
        result = await uc.execute(_webhook_payload(new_state=3))
        assert result is None
        uc._por_repo.save.assert_not_called()


class TestEditableCreation:
    @pytest.mark.asyncio
    async def test_resource_with_framework_creates_editable_bdc(self):
        tp = type("TP", (), {"id": uuid4()})()
        fc = type("FC", (), {"id": uuid4()})()
        uc = _make_use_case(consultant_type="resource", tp=tp, fc=fc)

        result = await uc.execute(_webhook_payload())

        assert result is not None
        assert result.status == PurchaseOrderRequestStatus.PENDING_VALIDATION
        assert result.framework_contract_id == fc.id
        assert result.third_party_id == tp.id
        assert result.daily_rate == Decimal("500")
        # BDC éditable → email commercial envoyé
        uc._email_service.send_commercial_validation_request.assert_awaited_once()


class TestLockedCreation:
    @pytest.mark.asyncio
    async def test_candidate_creates_locked_bdc(self):
        uc = _make_use_case(consultant_type="candidate")

        result = await uc.execute(_webhook_payload())

        assert result.status == PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT
        assert result.framework_contract_id is None
        assert result.third_party_id is None
        # BDC verrouillé → pas d'email commercial
        uc._email_service.send_commercial_validation_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_resource_without_framework_creates_locked_bdc(self):
        # Ressource mais aucun contrat cadre trouvé (tp=None)
        uc = _make_use_case(consultant_type="resource", tp=None)

        result = await uc.execute(_webhook_payload())

        assert result.status == PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT
        assert result.framework_contract_id is None


class TestIdempotence:
    @pytest.mark.asyncio
    async def test_existing_bdc_returned_without_duplicate(self):
        existing = type("POR", (), {"id": uuid4()})()
        uc = _make_use_case(existing_por=existing)

        result = await uc.execute(_webhook_payload())

        assert result is existing
        uc._por_repo.save.assert_not_called()
