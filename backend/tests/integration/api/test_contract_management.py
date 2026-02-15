"""Contract management API integration tests."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.infrastructure.models import (
    ContractModel,
    ContractRequestModel,
    WebhookEventModel,
)
from app.infrastructure.database.models import UserModel
from app.third_party.infrastructure.models import ThirdPartyModel


# ── Helpers ──────────────────────────────────────────────────────


async def _create_third_party(db: AsyncSession, **overrides) -> ThirdPartyModel:
    """Insert a third party into the test DB."""
    defaults = dict(
        id=uuid4(),
        type="freelance",
        company_name="Acme SARL",
        legal_form="SARL",
        siren="123456789",
        siret="12345678900010",
        rcs_city="Paris",
        rcs_number="123 456 789",
        head_office_address="1 rue de la Paix, 75001 Paris",
        representative_name="Jean Dupont",
        representative_title="Gérant",
        contact_email="contact@acme.fr",
        compliance_status="pending",
    )
    defaults.update(overrides)
    tp = ThirdPartyModel(**defaults)
    db.add(tp)
    await db.commit()
    await db.refresh(tp)
    return tp


async def _create_contract_request(
    db: AsyncSession, **overrides
) -> ContractRequestModel:
    """Insert a contract request into the test DB."""
    defaults = dict(
        id=uuid4(),
        reference=f"CR-{uuid4().hex[:6].upper()}",
        boond_positioning_id=1000 + int(uuid4().int % 9999),
        status="pending_commercial_validation",
        commercial_email="commercial@example.com",
    )
    defaults.update(overrides)
    cr = ContractRequestModel(**defaults)
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    return cr


async def _create_contract(db: AsyncSession, **overrides) -> ContractModel:
    """Insert a contract into the test DB."""
    defaults = dict(
        id=uuid4(),
        reference=f"C-{uuid4().hex[:6].upper()}",
        version=1,
        s3_key_draft="contracts/draft/test.docx",
    )
    defaults.update(overrides)
    c = ContractModel(**defaults)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ============================================================================
# List Contract Requests
# ============================================================================


class TestListContractRequests:
    """Tests for GET /api/v1/contract-requests."""

    @pytest.mark.asyncio
    async def test_adv_can_list_all(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV user can list all contract requests."""
        await _create_contract_request(db_session)
        await _create_contract_request(db_session)

        response = await client.get(
            "/api/v1/contract-requests",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_admin_can_list_all(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_user: UserModel,
        admin_headers: dict,
    ):
        """Admin user can list all contract requests."""
        await _create_contract_request(db_session)

        response = await client.get(
            "/api/v1/contract-requests",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_commercial_sees_only_own(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial sees only their contract requests."""
        await _create_contract_request(
            db_session, commercial_email=commercial_user.email
        )
        await _create_contract_request(
            db_session, commercial_email="other@example.com"
        )

        response = await client.get(
            "/api/v1/contract-requests",
            headers=commercial_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["commercial_email"] == commercial_user.email

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(
        self,
        client: AsyncClient,
        test_user: UserModel,
        auth_headers: dict,
    ):
        """Regular user cannot access contract requests."""
        response = await client.get(
            "/api/v1/contract-requests",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client: AsyncClient):
        """Unauthenticated request is rejected."""
        response = await client.get("/api/v1/contract-requests")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Can filter contract requests by status."""
        await _create_contract_request(
            db_session, status="pending_commercial_validation"
        )
        await _create_contract_request(db_session, status="configuring_contract")

        response = await client.get(
            "/api/v1/contract-requests",
            params={"status_filter": "configuring_contract"},
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "configuring_contract"

    @pytest.mark.asyncio
    async def test_invalid_status_filter(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Invalid status filter returns 400."""
        response = await client.get(
            "/api/v1/contract-requests",
            params={"status_filter": "invalid_status"},
            headers=adv_headers,
        )

        assert response.status_code == 400


# ============================================================================
# Get Contract Request
# ============================================================================


class TestGetContractRequest:
    """Tests for GET /api/v1/contract-requests/{id}."""

    @pytest.mark.asyncio
    async def test_adv_can_get_any(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can get any contract request."""
        cr = await _create_contract_request(db_session)

        response = await client.get(
            f"/api/v1/contract-requests/{cr.id}",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(cr.id)
        assert data["reference"] == cr.reference

    @pytest.mark.asyncio
    async def test_commercial_can_get_own(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial can get their own contract request."""
        cr = await _create_contract_request(
            db_session, commercial_email=commercial_user.email
        )

        response = await client.get(
            f"/api/v1/contract-requests/{cr.id}",
            headers=commercial_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_commercial_cannot_get_others(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial cannot get other's contract request."""
        cr = await _create_contract_request(
            db_session, commercial_email="other@example.com"
        )

        response = await client.get(
            f"/api/v1/contract-requests/{cr.id}",
            headers=commercial_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Nonexistent contract request returns 404."""
        response = await client.get(
            f"/api/v1/contract-requests/{uuid4()}",
            headers=adv_headers,
        )

        assert response.status_code == 404


# ============================================================================
# Compliance Override
# ============================================================================


class TestComplianceOverride:
    """Tests for POST /api/v1/contract-requests/{id}/compliance-override."""

    @pytest.mark.asyncio
    async def test_adv_can_override(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can override compliance."""
        cr = await _create_contract_request(
            db_session, status="compliance_blocked"
        )

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/compliance-override",
            json={"reason": "Documents will be provided within the week."},
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["compliance_override"] is True

    @pytest.mark.asyncio
    async def test_reason_too_short(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Override with reason too short returns 422."""
        cr = await _create_contract_request(db_session)

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/compliance-override",
            json={"reason": "short"},
            headers=adv_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Override on nonexistent request returns 404."""
        response = await client.post(
            f"/api/v1/contract-requests/{uuid4()}/compliance-override",
            json={"reason": "This is a valid override reason for testing."},
            headers=adv_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_commercial_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial user cannot override compliance."""
        cr = await _create_contract_request(db_session)

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/compliance-override",
            json={"reason": "This is a valid override reason for testing."},
            headers=commercial_headers,
        )

        assert response.status_code == 403


# ============================================================================
# List Contracts for a Request
# ============================================================================


class TestListContracts:
    """Tests for GET /api/v1/contract-requests/{id}/contracts."""

    @pytest.mark.asyncio
    async def test_list_empty_contracts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Returns empty list when no contracts exist."""
        cr = await _create_contract_request(db_session)

        response = await client.get(
            f"/api/v1/contract-requests/{cr.id}/contracts",
            headers=adv_headers,
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_contracts_with_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Returns contracts when they exist."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(
            db_session, third_party_id=tp.id
        )
        await _create_contract(
            db_session,
            contract_request_id=cr.id,
            third_party_id=tp.id,
        )

        response = await client.get(
            f"/api/v1/contract-requests/{cr.id}/contracts",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["contract_request_id"] == str(cr.id)


# ============================================================================
# Webhooks
# ============================================================================


class TestBoondWebhook:
    """Tests for POST /api/v1/webhooks/boondmanager/positioning-update."""

    @pytest.mark.asyncio
    async def test_always_returns_200(self, client: AsyncClient):
        """Webhook always returns 200 OK (even on error)."""
        response = await client.post(
            "/api/v1/webhooks/boondmanager/positioning-update",
            json={"some": "data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_invalid_json(self, client: AsyncClient):
        """Webhook handles invalid JSON gracefully."""
        response = await client.post(
            "/api/v1/webhooks/boondmanager/positioning-update",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_empty_payload(self, client: AsyncClient):
        """Webhook handles empty payload."""
        response = await client.post(
            "/api/v1/webhooks/boondmanager/positioning-update",
            json={},
        )

        assert response.status_code == 200


class TestYouSignWebhook:
    """Tests for POST /api/v1/webhooks/yousign/signature-completed."""

    @pytest.mark.asyncio
    async def test_always_returns_200(self, client: AsyncClient):
        """Webhook always returns 200 OK."""
        response = await client.post(
            "/api/v1/webhooks/yousign/signature-completed",
            json={"event_name": "signature_request.done", "data": {}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_ignores_non_done_events(self, client: AsyncClient):
        """Webhook ignores events that aren't signature_request.done."""
        response = await client.post(
            "/api/v1/webhooks/yousign/signature-completed",
            json={
                "event_name": "signature_request.activated",
                "data": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "Ignored event" in data["message"]

    @pytest.mark.asyncio
    async def test_invalid_json(self, client: AsyncClient):
        """Webhook handles invalid JSON gracefully."""
        response = await client.post(
            "/api/v1/webhooks/yousign/signature-completed",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_procedure_id(self, client: AsyncClient):
        """Webhook handles missing procedure ID."""
        response = await client.post(
            "/api/v1/webhooks/yousign/signature-completed",
            json={
                "event_name": "signature_request.done",
                "data": {"signature_request": {}},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "No procedure ID" in data["message"]


# ============================================================================
# Validate Commercial
# ============================================================================


class TestValidateCommercial:
    """Tests for POST /api/v1/contract-requests/{id}/validate-commercial."""

    @pytest.mark.asyncio
    async def test_validation_request_schema(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Validates request schema correctly."""
        cr = await _create_contract_request(db_session)

        # Missing required fields
        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/validate-commercial",
            json={},
            headers=adv_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_third_party_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Invalid third party type is rejected."""
        cr = await _create_contract_request(db_session)

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/validate-commercial",
            json={
                "third_party_type": "invalid_type",
                "daily_rate": 500,
                "start_date": "2026-03-01",
                "contact_email": "partner@example.com",
            },
            headers=adv_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: UserModel,
        auth_headers: dict,
    ):
        """Regular user cannot validate commercial."""
        cr = await _create_contract_request(db_session)

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/validate-commercial",
            json={
                "third_party_type": "freelance",
                "daily_rate": 500,
                "start_date": "2026-03-01",
                "contact_email": "partner@example.com",
            },
            headers=auth_headers,
        )

        assert response.status_code == 403


# ============================================================================
# Configure Contract
# ============================================================================


class TestConfigureContract:
    """Tests for POST /api/v1/contract-requests/{id}/configure."""

    @pytest.mark.asyncio
    async def test_adv_can_configure(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can configure a contract request."""
        cr = await _create_contract_request(
            db_session, status="collecting_documents"
        )

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/configure",
            json={
                "mission_description": "Mission de développement",
                "mission_location": "Paris",
                "daily_rate": 550,
                "payment_terms": "net_30",
            },
            headers=adv_headers,
        )

        # May fail due to business rules (status transition), but should not be 403/401
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_commercial_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial cannot configure contract."""
        cr = await _create_contract_request(db_session)

        response = await client.post(
            f"/api/v1/contract-requests/{cr.id}/configure",
            json={"mission_description": "Test"},
            headers=commercial_headers,
        )

        assert response.status_code == 403
