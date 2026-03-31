"""Tests for CreateContractRequestFromEntityUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contract_management.application.use_cases.create_contract_request_from_entity import (
    BOOND_CANDIDATE_STATE_AWAITING_CONTRACT,
    BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
    BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
    CreateContractRequestFromEntityUseCase,
)
from app.contract_management.domain.exceptions import WebhookDuplicateError


def _build_webhook_payload(entity_type: str, entity_id: int, new_state: int) -> list:
    """Build a Boond webhook payload for testing."""
    return [
        {
            "data": {
                "id": f"3_{entity_type}_{entity_id}",
                "type": "webhookevent",
                "attributes": {"type": "update"},
                "relationships": {
                    "dependsOn": {"id": str(entity_id), "type": entity_type},
                    "log": {"id": "99999", "type": "log"},
                },
                "included": [
                    {
                        "id": "99999",
                        "type": "log",
                        "attributes": {
                            "content": {
                                "context": {"id": str(entity_id)},
                                "diff": {"state": {"old": 0, "new": new_state}},
                            }
                        },
                    }
                ],
            }
        }
    ]


def _make_use_case(**overrides) -> CreateContractRequestFromEntityUseCase:
    """Create use case with mock dependencies."""
    cr_repo = AsyncMock()
    cr_repo.get_next_provisional_reference = AsyncMock(return_value="PROV-2026-0001")
    cr_repo.get_latest_by_resource_id = AsyncMock(return_value=None)
    cr_repo.save = AsyncMock(side_effect=lambda cr: cr)

    webhook_repo = AsyncMock()
    webhook_repo.exists = AsyncMock(return_value=False)
    webhook_repo.save = AsyncMock()

    crm_service = AsyncMock()
    crm_service.get_candidate_info = AsyncMock(return_value={
        "id": 123,
        "civility": "M.",
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean.dupont@example.com",
        "phone": "+33 6 12 34 56 78",
    })

    email_service = AsyncMock()
    email_service.send_commercial_validation_request = AsyncMock(return_value=True)

    defaults = {
        "contract_request_repository": cr_repo,
        "webhook_event_repository": webhook_repo,
        "crm_service": crm_service,
        "email_service": email_service,
        "frontend_url": "https://bobby.example.com",
    }
    defaults.update(overrides)
    return CreateContractRequestFromEntityUseCase(**defaults)


class TestParseWebhookEvent:
    """Test webhook payload parsing for candidate and resource events."""

    def test_parse_candidate_webhook(self):
        """Should extract candidate ID and state from webhook payload."""
        payload = _build_webhook_payload("candidate", 42, 11)
        data = payload[0]["data"]
        entity_id, state = CreateContractRequestFromEntityUseCase._parse_webhook_event(
            data, "candidate"
        )
        assert entity_id == 42
        assert state == 11

    def test_parse_resource_webhook_state_4(self):
        """Should extract resource ID and state 4 from webhook payload."""
        payload = _build_webhook_payload("resource", 99, 4)
        data = payload[0]["data"]
        entity_id, state = CreateContractRequestFromEntityUseCase._parse_webhook_event(
            data, "resource"
        )
        assert entity_id == 99
        assert state == 4

    def test_parse_resource_webhook_state_5(self):
        """Should extract resource ID and state 5 from webhook payload."""
        payload = _build_webhook_payload("resource", 77, 5)
        data = payload[0]["data"]
        entity_id, state = CreateContractRequestFromEntityUseCase._parse_webhook_event(
            data, "resource"
        )
        assert entity_id == 77
        assert state == 5

    def test_wrong_entity_type_returns_none(self):
        """Should return None when dependsOn type doesn't match expected."""
        payload = _build_webhook_payload("positioning", 100, 7)
        data = payload[0]["data"]
        entity_id, state = CreateContractRequestFromEntityUseCase._parse_webhook_event(
            data, "candidate"
        )
        assert entity_id is None

    def test_missing_depends_on_returns_none(self):
        """Should return None when dependsOn is missing."""
        data = {
            "type": "webhookevent",
            "relationships": {},
            "included": [],
        }
        entity_id, state = CreateContractRequestFromEntityUseCase._parse_webhook_event(
            data, "candidate"
        )
        assert entity_id is None


class TestResolveTriggerType:
    """Test trigger type resolution."""

    def test_candidate_11(self):
        result = CreateContractRequestFromEntityUseCase._resolve_trigger_type("candidate", 11)
        assert result == "candidat_11"

    def test_resource_4(self):
        result = CreateContractRequestFromEntityUseCase._resolve_trigger_type("resource", 4)
        assert result == "ressource_4"

    def test_resource_5(self):
        result = CreateContractRequestFromEntityUseCase._resolve_trigger_type("resource", 5)
        assert result == "ressource_5"


class TestExecuteCandidateState11:
    """Test contract request creation from candidate state 11."""

    @pytest.mark.asyncio
    async def test_creates_contract_request(self):
        """Should create a CR with trigger_type=candidat_11."""
        uc = _make_use_case()
        payload = _build_webhook_payload("candidate", 42, 11)

        result = await uc.execute(
            payload=payload,
            entity_type="candidate",
            expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
        )

        assert result is not None
        assert result.trigger_type == "candidat_11"
        assert result.boond_candidate_id == 42
        assert result.boond_resource_id is None
        assert result.consultant_first_name == "Jean"
        assert result.consultant_last_name == "Dupont"
        assert result.provisional_reference == "PROV-2026-0001"

    @pytest.mark.asyncio
    async def test_filters_wrong_state(self):
        """Should return None when state doesn't match expected."""
        uc = _make_use_case()
        payload = _build_webhook_payload("candidate", 42, 7)

        result = await uc.execute(
            payload=payload,
            entity_type="candidate",
            expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_idempotence_duplicate(self):
        """Should raise WebhookDuplicateError on duplicate event."""
        webhook_repo = AsyncMock()
        webhook_repo.exists = AsyncMock(return_value=True)

        uc = _make_use_case(webhook_event_repository=webhook_repo)
        payload = _build_webhook_payload("candidate", 42, 11)

        with pytest.raises(WebhookDuplicateError):
            await uc.execute(
                payload=payload,
                entity_type="candidate",
                expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
            )

    @pytest.mark.asyncio
    async def test_saves_webhook_event(self):
        """Should save webhook event for idempotence."""
        uc = _make_use_case()
        payload = _build_webhook_payload("candidate", 42, 11)

        await uc.execute(
            payload=payload,
            entity_type="candidate",
            expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
        )

        uc._webhook_repo.save.assert_called_once()
        call_args = uc._webhook_repo.save.call_args
        assert call_args[1]["event_id"] == "candidate_state_42_11"

    @pytest.mark.asyncio
    async def test_handles_boond_entity_not_found(self):
        """Should return None when Boond entity info is not found."""
        crm = AsyncMock()
        crm.get_candidate_info = AsyncMock(return_value=None)

        uc = _make_use_case(crm_service=crm)
        payload = _build_webhook_payload("candidate", 42, 11)

        result = await uc.execute(
            payload=payload,
            entity_type="candidate",
            expected_states=[BOOND_CANDIDATE_STATE_AWAITING_CONTRACT],
        )

        assert result is None


class TestExecuteResourceState4:
    """Test contract request creation from resource state 4 (re-contractualization)."""

    @pytest.mark.asyncio
    async def test_creates_cr_with_trigger_ressource_4(self):
        """Should create a CR with trigger_type=ressource_4."""
        uc = _make_use_case()
        payload = _build_webhook_payload("resource", 99, 4)

        result = await uc.execute(
            payload=payload,
            entity_type="resource",
            expected_states=[
                BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
                BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
            ],
        )

        assert result is not None
        assert result.trigger_type == "ressource_4"
        assert result.boond_resource_id == 99
        assert result.boond_candidate_id is None

    @pytest.mark.asyncio
    async def test_links_previous_cr(self):
        """Should link to previous CR when found."""
        from uuid import uuid4

        previous_cr = MagicMock()
        previous_cr.id = uuid4()
        previous_cr.commercial_email = "commercial@example.com"

        cr_repo = AsyncMock()
        cr_repo.get_next_provisional_reference = AsyncMock(return_value="PROV-2026-0002")
        cr_repo.get_latest_by_resource_id = AsyncMock(return_value=previous_cr)
        cr_repo.save = AsyncMock(side_effect=lambda cr: cr)

        uc = _make_use_case(contract_request_repository=cr_repo)
        payload = _build_webhook_payload("resource", 99, 4)

        result = await uc.execute(
            payload=payload,
            entity_type="resource",
            expected_states=[
                BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
                BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
            ],
        )

        assert result.previous_contract_request_id == previous_cr.id
        assert result.commercial_email == "commercial@example.com"


class TestExecuteResourceState5:
    """Test contract request creation from resource state 5 (company change)."""

    @pytest.mark.asyncio
    async def test_creates_cr_with_trigger_ressource_5(self):
        """Should create a CR with trigger_type=ressource_5."""
        uc = _make_use_case()
        payload = _build_webhook_payload("resource", 77, 5)

        result = await uc.execute(
            payload=payload,
            entity_type="resource",
            expected_states=[
                BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT,
                BOOND_RESOURCE_STATE_CONTRACT_CHANGE,
            ],
        )

        assert result is not None
        assert result.trigger_type == "ressource_5"
        assert result.boond_resource_id == 77
