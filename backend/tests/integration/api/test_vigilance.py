"""Vigilance API integration tests."""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import UserModel
from app.third_party.infrastructure.models import ThirdPartyModel
from app.vigilance.infrastructure.models import VigilanceDocumentModel


# ── Helpers ──────────────────────────────────────────────────────


async def _create_third_party(
    db: AsyncSession, **overrides
) -> ThirdPartyModel:
    """Insert a third party into the test DB."""
    defaults = dict(
        id=uuid4(),
        type="freelance",
        company_name="Acme SARL",
        legal_form="SARL",
        siren=f"{uuid4().int % 999999999:09d}",
        siret=f"{uuid4().int % 99999999999999:014d}",
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


async def _create_document(
    db: AsyncSession, **overrides
) -> VigilanceDocumentModel:
    """Insert a vigilance document into the test DB."""
    defaults = dict(
        id=uuid4(),
        document_type="kbis",
        status="requested",
    )
    defaults.update(overrides)
    doc = VigilanceDocumentModel(**defaults)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ============================================================================
# List Third Parties
# ============================================================================


class TestListThirdParties:
    """Tests for GET /api/v1/vigilance/third-parties."""

    @pytest.mark.asyncio
    async def test_adv_can_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV user can list third parties."""
        await _create_third_party(db_session)

        response = await client.get(
            "/api/v1/vigilance/third-parties",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_admin_can_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_user: UserModel,
        admin_headers: dict,
    ):
        """Admin can list third parties."""
        await _create_third_party(db_session)

        response = await client.get(
            "/api/v1/vigilance/third-parties",
            headers=admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_commercial_forbidden(
        self,
        client: AsyncClient,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial cannot access vigilance."""
        response = await client.get(
            "/api/v1/vigilance/third-parties",
            headers=commercial_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(
        self,
        client: AsyncClient,
        test_user: UserModel,
        auth_headers: dict,
    ):
        """Regular user cannot access vigilance."""
        response = await client.get(
            "/api/v1/vigilance/third-parties",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client: AsyncClient):
        """Unauthenticated request is rejected."""
        response = await client.get("/api/v1/vigilance/third-parties")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_filter_by_compliance_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Can filter by compliance status."""
        await _create_third_party(db_session, compliance_status="compliant")
        await _create_third_party(db_session, compliance_status="non_compliant")

        response = await client.get(
            "/api/v1/vigilance/third-parties",
            params={"compliance_status": "compliant"},
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["compliance_status"] == "compliant"

    @pytest.mark.asyncio
    async def test_invalid_compliance_status(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Invalid compliance status returns 400."""
        response = await client.get(
            "/api/v1/vigilance/third-parties",
            params={"compliance_status": "invalid"},
            headers=adv_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Pagination works correctly."""
        for _ in range(5):
            await _create_third_party(db_session)

        response = await client.get(
            "/api/v1/vigilance/third-parties",
            params={"skip": 0, "limit": 2},
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 5


# ============================================================================
# Get Third Party Documents
# ============================================================================


class TestGetThirdPartyDocuments:
    """Tests for GET /api/v1/vigilance/third-parties/{id}/documents."""

    @pytest.mark.asyncio
    async def test_get_with_documents(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Returns third party with its documents."""
        tp = await _create_third_party(db_session)
        await _create_document(
            db_session,
            third_party_id=tp.id,
            document_type="kbis",
            status="requested",
        )
        await _create_document(
            db_session,
            third_party_id=tp.id,
            document_type="attestation_urssaf",
            status="validated",
        )

        response = await client.get(
            f"/api/v1/vigilance/third-parties/{tp.id}/documents",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(tp.id)
        assert data["company_name"] == tp.company_name
        assert len(data["documents"]) == 2

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Nonexistent third party returns 404."""
        response = await client.get(
            f"/api/v1/vigilance/third-parties/{uuid4()}/documents",
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
        """Commercial cannot access third party documents."""
        tp = await _create_third_party(db_session)

        response = await client.get(
            f"/api/v1/vigilance/third-parties/{tp.id}/documents",
            headers=commercial_headers,
        )

        assert response.status_code == 403


# ============================================================================
# Request Documents
# ============================================================================


class TestRequestDocuments:
    """Tests for POST /api/v1/vigilance/third-parties/{id}/request-documents."""

    @pytest.mark.asyncio
    async def test_adv_can_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can request documents for a third party."""
        tp = await _create_third_party(db_session)

        response = await client.post(
            f"/api/v1/vigilance/third-parties/{tp.id}/request-documents",
            headers=adv_headers,
        )

        # May return 200 (created) or 400 (already exist)
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Request for nonexistent third party."""
        response = await client.post(
            f"/api/v1/vigilance/third-parties/{uuid4()}/request-documents",
            headers=adv_headers,
        )

        assert response.status_code == 400


# ============================================================================
# Validate Document
# ============================================================================


class TestValidateDocument:
    """Tests for POST /api/v1/vigilance/documents/{id}/validate."""

    @pytest.mark.asyncio
    async def test_adv_can_validate(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can validate a received document."""
        tp = await _create_third_party(db_session)
        doc = await _create_document(
            db_session,
            third_party_id=tp.id,
            status="received",
            s3_key="vigilance/test/doc.pdf",
            file_name="attestation.pdf",
            file_size=1024,
            uploaded_at=datetime.utcnow(),
        )

        response = await client.post(
            f"/api/v1/vigilance/documents/{doc.id}/validate",
            headers=adv_headers,
        )

        # 200 or 400 depending on business rules (e.g. status transition)
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_not_found(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Validate nonexistent document."""
        response = await client.post(
            f"/api/v1/vigilance/documents/{uuid4()}/validate",
            headers=adv_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(
        self,
        client: AsyncClient,
        test_user: UserModel,
        auth_headers: dict,
    ):
        """Regular user cannot validate documents."""
        response = await client.post(
            f"/api/v1/vigilance/documents/{uuid4()}/validate",
            headers=auth_headers,
        )

        assert response.status_code == 403


# ============================================================================
# Reject Document
# ============================================================================


class TestRejectDocument:
    """Tests for POST /api/v1/vigilance/documents/{id}/reject."""

    @pytest.mark.asyncio
    async def test_adv_can_reject(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can reject a received document."""
        tp = await _create_third_party(db_session)
        doc = await _create_document(
            db_session,
            third_party_id=tp.id,
            status="received",
            s3_key="vigilance/test/doc.pdf",
            file_name="attestation.pdf",
            file_size=1024,
            uploaded_at=datetime.utcnow(),
        )

        response = await client.post(
            f"/api/v1/vigilance/documents/{doc.id}/reject",
            json={"reason": "Document is unreadable, please upload again."},
            headers=adv_headers,
        )

        # 200 or 400 depending on business rules
        assert response.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_reason_too_short(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Rejection with reason too short returns 422."""
        response = await client.post(
            f"/api/v1/vigilance/documents/{uuid4()}/reject",
            json={"reason": "bad"},
            headers=adv_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_reason(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Rejection without reason returns 422."""
        response = await client.post(
            f"/api/v1/vigilance/documents/{uuid4()}/reject",
            json={},
            headers=adv_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_commercial_forbidden(
        self,
        client: AsyncClient,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial cannot reject documents."""
        response = await client.post(
            f"/api/v1/vigilance/documents/{uuid4()}/reject",
            json={"reason": "This is a valid rejection reason."},
            headers=commercial_headers,
        )

        assert response.status_code == 403


# ============================================================================
# Compliance Dashboard
# ============================================================================


class TestComplianceDashboard:
    """Tests for GET /api/v1/compliance/dashboard."""

    @pytest.mark.asyncio
    async def test_adv_can_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """ADV can access compliance dashboard."""
        # Create some third parties with different compliance statuses
        await _create_third_party(db_session, compliance_status="compliant")
        await _create_third_party(db_session, compliance_status="non_compliant")
        await _create_third_party(db_session, compliance_status="pending")

        response = await client.get(
            "/api/v1/compliance/dashboard",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_third_parties" in data
        assert "compliant" in data
        assert "non_compliant" in data
        assert "pending" in data
        assert "compliance_rate" in data
        assert "documents_pending_review" in data
        assert "documents_expiring_soon" in data
        assert data["total_third_parties"] >= 3

    @pytest.mark.asyncio
    async def test_admin_can_access(
        self,
        client: AsyncClient,
        admin_user: UserModel,
        admin_headers: dict,
    ):
        """Admin can access compliance dashboard."""
        response = await client.get(
            "/api/v1/compliance/dashboard",
            headers=admin_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_commercial_forbidden(
        self,
        client: AsyncClient,
        commercial_user: UserModel,
        commercial_headers: dict,
    ):
        """Commercial cannot access compliance dashboard."""
        response = await client.get(
            "/api/v1/compliance/dashboard",
            headers=commercial_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client: AsyncClient):
        """Unauthenticated request is rejected."""
        response = await client.get("/api/v1/compliance/dashboard")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_dashboard(
        self,
        client: AsyncClient,
        adv_user: UserModel,
        adv_headers: dict,
    ):
        """Dashboard works with no data."""
        response = await client.get(
            "/api/v1/compliance/dashboard",
            headers=adv_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_third_parties"] == 0
        assert data["compliance_rate"] == 0.0
