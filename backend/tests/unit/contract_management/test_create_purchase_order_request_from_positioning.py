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
    """Build a Boond positioning-update webhook payload with a state diff (test form)."""
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


def _webhook_payload_stateless(positioning_id: int = 433) -> list:
    """Build the REAL Boond payload: webhookevent with dependsOn but NO state.

    Matches docs/contracts/webhook-configuration.md — the state is not in the
    payload and must be fetched from the API.
    """
    return [
        {
            "data": {
                "id": "6_69cbd09b4ae56",
                "type": "webhookevent",
                "attributes": {"type": "update"},
                "relationships": {
                    "webhook": {"id": "6", "type": "webhook"},
                    "dependsOn": {"id": str(positioning_id), "type": "positioning"},
                    "log": {"id": "123634", "type": "log"},
                },
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
    positioning_state: int = 7,
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
            "state": positioning_state,
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
    # Par défaut, un candidat n'est PAS converti en ressource (→ pas de résolution).
    crm.resolve_resource_id = AsyncMock(return_value=None)

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

    @pytest.mark.asyncio
    async def test_real_leaving_state_7_payload_filtered_without_api_call(self):
        """Vrai payload Boond 7→0 (sortie de l'état 7) : filtré, sans appel API."""
        uc = _make_use_case()
        payload = [
            {
                "data": {
                    "id": "8_6a4fba3bbc361",
                    "type": "webhookevent",
                    "attributes": {"type": "update"},
                    "relationships": {
                        "webhook": {"id": "8", "type": "webhook"},
                        "dependsOn": {"id": "532", "type": "positioning"},
                        "log": {"id": "135564", "type": "log"},
                    },
                    "included": [
                        {"id": "1", "type": "resource",
                         "attributes": {"lastName": "EL KHODJA", "firstName": "Chérif"}},
                        {"id": "135564", "type": "log",
                         "attributes": {"content": {"diff": {"state": {"old": 7, "new": 0}}}}},
                    ],
                }
            }
        ]

        result = await uc.execute(payload)

        assert result is None
        uc._crm.get_positioning.assert_not_called()  # filtré avant tout appel API
        uc._por_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_stateless_payload_uses_api_state_7(self):
        """Real Boond payload (no state) → state fetched from API == 7 → BDC created."""
        tp = type("TP", (), {"id": uuid4()})()
        fc = type("FC", (), {"id": uuid4()})()
        uc = _make_use_case(consultant_type="resource", tp=tp, fc=fc, positioning_state=7)

        result = await uc.execute(_webhook_payload_stateless())

        assert result is not None
        assert result.status == PurchaseOrderRequestStatus.PENDING_VALIDATION

    @pytest.mark.asyncio
    async def test_stateless_payload_api_state_not_7_filtered(self):
        """Real payload but the positioning is no longer in state 7 → skipped."""
        uc = _make_use_case(positioning_state=8)

        result = await uc.execute(_webhook_payload_stateless())

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
    async def test_converted_candidate_with_framework_is_editable(self):
        """Positionnement référençant encore le candidat, mais converti en
        ressource rattachée à un contrat cadre actif → BDC éditable."""
        tp = type("TP", (), {"id": uuid4()})()
        fc = type("FC", (), {"id": uuid4()})()
        uc = _make_use_case(consultant_type="candidate", tp=tp, fc=fc)
        uc._crm.resolve_resource_id = AsyncMock(return_value=999)  # candidat → ressource

        result = await uc.execute(_webhook_payload())

        assert result.status == PurchaseOrderRequestStatus.PENDING_VALIDATION
        assert result.framework_contract_id == fc.id

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

    @pytest.mark.asyncio
    async def test_recreates_after_cancel_clears_stale_dedup(self):
        """BDC précédent annulé (aucun actif) + dédup présente → purge + recrée."""
        tp = type("TP", (), {"id": uuid4()})()
        fc = type("FC", (), {"id": uuid4()})()
        uc = _make_use_case(consultant_type="resource", tp=tp, fc=fc)
        # Aucun BDC actif (annulé), mais l'événement a déjà été dédupliqué.
        uc._webhook_repo.exists = AsyncMock(return_value=True)

        result = await uc.execute(_webhook_payload())

        assert result is not None
        assert result.status == PurchaseOrderRequestStatus.PENDING_VALIDATION
        uc._webhook_repo.delete_by_prefix.assert_awaited()  # dédup purgée
        uc._por_repo.save.assert_awaited()  # nouveau BDC créé
