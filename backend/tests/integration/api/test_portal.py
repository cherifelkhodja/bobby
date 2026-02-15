"""Portal (magic link) API integration tests."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.infrastructure.models import (
    ContractModel,
    ContractRequestModel,
)
from app.infrastructure.database.models import UserModel
from app.third_party.infrastructure.models import MagicLinkModel, ThirdPartyModel
from app.vigilance.infrastructure.models import VigilanceDocumentModel


# ── Helpers ──────────────────────────────────────────────────────


async def _create_third_party(db: AsyncSession, **overrides) -> ThirdPartyModel:
    """Insert a third party into the test DB."""
    defaults = dict(
        id=uuid4(),
        type="freelance",
        company_name="Portal Test SARL",
        legal_form="SARL",
        siren=f"{uuid4().int % 999999999:09d}",
        siret=f"{uuid4().int % 99999999999999:014d}",
        rcs_city="Lyon",
        rcs_number="987 654 321",
        head_office_address="10 rue du Test, 69001 Lyon",
        representative_name="Marie Martin",
        representative_title="Gérante",
        contact_email="portal@test.fr",
        compliance_status="pending",
    )
    defaults.update(overrides)
    tp = ThirdPartyModel(**defaults)
    db.add(tp)
    await db.commit()
    await db.refresh(tp)
    return tp


async def _create_magic_link(
    db: AsyncSession,
    third_party_id,
    purpose: str = "document_upload",
    **overrides,
) -> MagicLinkModel:
    """Insert a magic link into the test DB."""
    defaults = dict(
        id=uuid4(),
        token=f"test-token-{uuid4().hex[:16]}",
        third_party_id=third_party_id,
        purpose=purpose,
        email_sent_to="portal@test.fr",
        expires_at=datetime.utcnow() + timedelta(days=7),
        is_revoked=False,
    )
    defaults.update(overrides)
    ml = MagicLinkModel(**defaults)
    db.add(ml)
    await db.commit()
    await db.refresh(ml)
    return ml


async def _create_contract_request(
    db: AsyncSession, **overrides
) -> ContractRequestModel:
    """Insert a contract request into the test DB."""
    defaults = dict(
        id=uuid4(),
        reference=f"CR-{uuid4().hex[:6].upper()}",
        boond_positioning_id=2000 + int(uuid4().int % 9999),
        status="draft_sent_to_partner",
        commercial_email="commercial@example.com",
    )
    defaults.update(overrides)
    cr = ContractRequestModel(**defaults)
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    return cr


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
# Portal Info (verify magic link)
# ============================================================================


class TestGetPortalInfo:
    """Tests for GET /api/v1/portal/{token}."""

    @pytest.mark.asyncio
    async def test_valid_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Valid magic link returns portal info."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(db_session, tp.id)

        response = await client.get(f"/api/v1/portal/{ml.token}")

        assert response.status_code == 200
        data = response.json()
        assert data["third_party"]["id"] == str(tp.id)
        assert data["third_party"]["company_name"] == tp.company_name
        assert data["purpose"] == "document_upload"

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Invalid token returns 404."""
        response = await client.get("/api/v1/portal/invalid-token-xyz")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Expired magic link returns 410."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = await client.get(f"/api/v1/portal/{ml.token}")
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_revoked_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Revoked magic link returns 410."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            is_revoked=True,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}")
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_contract_review_purpose(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Contract review magic link returns contract_request_id."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(db_session, third_party_id=tp.id)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=cr.id,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}")

        assert response.status_code == 200
        data = response.json()
        assert data["purpose"] == "contract_review"
        assert data["contract_request_id"] == str(cr.id)


# ============================================================================
# Portal Documents List
# ============================================================================


class TestGetPortalDocuments:
    """Tests for GET /api/v1/portal/{token}/documents."""

    @pytest.mark.asyncio
    async def test_list_documents(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Returns documents for the third party."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(db_session, tp.id, purpose="document_upload")
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
            status="requested",
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["third_party_id"] == str(tp.id)
        assert len(data["documents"]) == 2

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Invalid token returns 404."""
        response = await client.get("/api/v1/portal/bad-token/documents")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_purpose_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Contract review link cannot list documents."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(db_session, third_party_id=tp.id)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=cr.id,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/documents")
        assert response.status_code == 403


# ============================================================================
# Portal Document Upload
# ============================================================================


class TestUploadPortalDocument:
    """Tests for POST /api/v1/portal/{token}/documents/{id}/upload."""

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Invalid token returns 404."""
        response = await client.post(
            f"/api/v1/portal/bad-token/documents/{uuid4()}/upload",
            files={"file": ("test.pdf", b"fake pdf", "application/pdf")},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_document_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Upload to nonexistent document returns 404."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(db_session, tp.id, purpose="document_upload")

        response = await client.post(
            f"/api/v1/portal/{ml.token}/documents/{uuid4()}/upload",
            files={"file": ("test.pdf", b"fake pdf", "application/pdf")},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_document_belongs_to_different_third_party(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Cannot upload document belonging to a different third party."""
        tp1 = await _create_third_party(db_session)
        tp2 = await _create_third_party(db_session)
        ml = await _create_magic_link(db_session, tp1.id, purpose="document_upload")
        doc = await _create_document(
            db_session, third_party_id=tp2.id
        )

        response = await client.post(
            f"/api/v1/portal/{ml.token}/documents/{doc.id}/upload",
            files={"file": ("test.pdf", b"fake pdf", "application/pdf")},
        )

        assert response.status_code == 404


# ============================================================================
# Contract Draft (portal)
# ============================================================================


class TestGetContractDraft:
    """Tests for GET /api/v1/portal/{token}/contract-draft."""

    @pytest.mark.asyncio
    async def test_get_draft_info(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Returns contract draft info for review."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(db_session, third_party_id=tp.id)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=cr.id,
        )
        await _create_contract(
            db_session,
            contract_request_id=cr.id,
            third_party_id=tp.id,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/contract-draft")

        assert response.status_code == 200
        data = response.json()
        assert data["contract_request_id"] == str(cr.id)
        assert "reference" in data
        assert "s3_key_draft" in data

    @pytest.mark.asyncio
    async def test_no_contract_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Returns 404 when no contract request linked."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=None,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/contract-draft")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_no_contract_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Returns 404 when contract request exists but no contract."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(db_session, third_party_id=tp.id)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=cr.id,
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/contract-draft")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_purpose_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Document upload link cannot get contract draft."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="document_upload",
        )

        response = await client.get(f"/api/v1/portal/{ml.token}/contract-draft")
        assert response.status_code == 403


# ============================================================================
# Contract Review
# ============================================================================


class TestSubmitContractReview:
    """Tests for POST /api/v1/portal/{token}/contract-review."""

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Invalid token returns 404."""
        response = await client.post(
            "/api/v1/portal/bad-token/contract-review",
            json={"decision": "approved"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_decision(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Invalid decision value returns 422."""
        tp = await _create_third_party(db_session)
        cr = await _create_contract_request(db_session, third_party_id=tp.id)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=cr.id,
        )

        response = await client.post(
            f"/api/v1/portal/{ml.token}/contract-review",
            json={"decision": "maybe"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_purpose_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Document upload link cannot review contract."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="document_upload",
        )

        response = await client.post(
            f"/api/v1/portal/{ml.token}/contract-review",
            json={"decision": "approved"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_no_contract_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Returns 404 when no contract request is linked."""
        tp = await _create_third_party(db_session)
        ml = await _create_magic_link(
            db_session,
            tp.id,
            purpose="contract_review",
            contract_request_id=None,
        )

        response = await client.post(
            f"/api/v1/portal/{ml.token}/contract-review",
            json={"decision": "approved"},
        )

        assert response.status_code == 404
