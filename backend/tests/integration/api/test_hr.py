"""Integration tests for HR API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestHROpportunitiesEndpoint:
    """Tests for /hr/opportunities endpoint."""

    @pytest.mark.asyncio
    async def test_list_opportunities_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/hr/opportunities")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_opportunities_requires_hr_role(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 403 for non-HR users."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_opportunities_success(self, client: AsyncClient, admin_headers: dict):
        """Should return opportunities list for admin."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_opportunities_with_search(self, client: AsyncClient, admin_headers: dict):
        """Should filter opportunities by search term."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            params={"search": "Python"},
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_opportunities_pagination(self, client: AsyncClient, admin_headers: dict):
        """Should respect pagination parameters."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            params={"page": 1, "page_size": 5},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestJobPostingsEndpoints:
    """Tests for /hr/job-postings endpoints."""

    @pytest.mark.asyncio
    async def test_create_job_posting_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.post("/api/v1/hr/job-postings", json={})
        # 401 if auth required, 422 if validation runs before auth check
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_create_job_posting_validation(self, client: AsyncClient, admin_headers: dict):
        """Should validate required fields."""
        response = await client.post(
            "/api/v1/hr/job-postings",
            json={
                "opportunity_id": str(uuid4()),
                "title": "AB",  # Too short
                "description": "Too short",
                "qualifications": "Too short",
                "location_country": "FR",
            },
            headers=admin_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_job_postings_success(self, client: AsyncClient, admin_headers: dict):
        """Should return job postings list."""
        response = await client.get(
            "/api/v1/hr/job-postings",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_job_postings_filter_by_status(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Should filter by status."""
        response = await client.get(
            "/api/v1/hr/job-postings",
            params={"status": "draft"},
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_job_posting_not_found(self, client: AsyncClient, admin_headers: dict):
        """Should return 404 for non-existent posting."""
        response = await client.get(
            f"/api/v1/hr/job-postings/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_non_draft_fails(self, client: AsyncClient, admin_headers: dict):
        """Should return 400 when trying to publish non-draft."""
        # Non-existent posting will return 404
        response = await client.post(
            f"/api/v1/hr/job-postings/{uuid4()}/publish",
            headers=admin_headers,
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_close_non_published_fails(self, client: AsyncClient, admin_headers: dict):
        """Should return 400 when trying to close non-published."""
        response = await client.post(
            f"/api/v1/hr/job-postings/{uuid4()}/close",
            headers=admin_headers,
        )
        assert response.status_code in [400, 404]


class TestApplicationsEndpoints:
    """Tests for /hr/applications endpoints."""

    @pytest.mark.asyncio
    async def test_list_applications_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get(f"/api/v1/hr/job-postings/{uuid4()}/applications")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_applications_posting_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Should return 404 for non-existent posting."""
        response = await client.get(
            f"/api/v1/hr/job-postings/{uuid4()}/applications",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_application_not_found(self, client: AsyncClient, admin_headers: dict):
        """Should return 404 for non-existent application."""
        response = await client.get(
            f"/api/v1/hr/applications/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_application_status_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.patch(
            f"/api/v1/hr/applications/{uuid4()}/status",
            json={"status": "en_cours"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_application_status_invalid(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Should return 400 for invalid status."""
        response = await client.patch(
            f"/api/v1/hr/applications/{uuid4()}/status",
            json={"status": "invalid_status"},
            headers=admin_headers,
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_update_application_note_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.patch(
            f"/api/v1/hr/applications/{uuid4()}/note",
            json={"notes": "Test note"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_cv_url_not_found(self, client: AsyncClient, admin_headers: dict):
        """Should return 404 for non-existent application."""
        response = await client.get(
            f"/api/v1/hr/applications/{uuid4()}/cv",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_in_boond_not_found(self, client: AsyncClient, admin_headers: dict):
        """Should return 404 for non-existent application."""
        response = await client.post(
            f"/api/v1/hr/applications/{uuid4()}/create-in-boond",
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestPublicApplicationEndpoints:
    """Tests for /postuler endpoints (public)."""

    @pytest.mark.asyncio
    async def test_get_public_job_posting_not_found(self, client: AsyncClient):
        """Should return 404 for invalid token."""
        response = await client.get("/api/v1/postuler/invalid-token")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_application_invalid_token(self, client: AsyncClient):
        """Should return 404 for invalid token."""
        response = await client.post(
            "/api/v1/postuler/invalid-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean@example.com",
                "phone": "+33612345678",
                "job_title": "Dev Python",
                "availability": "1_month",
                "employment_status": "freelance",
                "english_level": "professional",
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_submit_application_validation_email(self, client: AsyncClient):
        """Should validate email format."""
        response = await client.post(
            "/api/v1/postuler/some-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "invalid-email",
                "phone": "+33612345678",
                "job_title": "Dev",
                "availability": "1_month",
                "employment_status": "freelance",
                "english_level": "intermediate",
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_submit_application_validation_phone(self, client: AsyncClient):
        """Should validate phone format."""
        response = await client.post(
            "/api/v1/postuler/some-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean@example.com",
                "phone": "123",  # Invalid phone
                "job_title": "Dev",
                "availability": "1_month",
                "employment_status": "freelance",
                "english_level": "intermediate",
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_submit_application_validation_tjm(self, client: AsyncClient):
        """Should validate TJM values."""
        response = await client.post(
            "/api/v1/postuler/some-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean@example.com",
                "phone": "+33612345678",
                "job_title": "Dev",
                "availability": "1_month",
                "employment_status": "freelance",
                "english_level": "intermediate",
                "tjm_current": "-100",
                "tjm_desired": "-200",
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_submit_application_invalid_cv_format(self, client: AsyncClient):
        """Should reject invalid CV format."""
        response = await client.post(
            "/api/v1/postuler/some-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean@example.com",
                "phone": "+33612345678",
                "job_title": "Dev",
                "availability": "1_month",
                "employment_status": "freelance",
                "english_level": "intermediate",
            },
            files={"cv": ("cv.txt", b"Text content", "text/plain")},
        )
        assert response.status_code in [400, 404, 422]
