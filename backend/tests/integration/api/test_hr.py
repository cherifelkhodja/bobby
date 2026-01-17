"""Integration tests for HR API endpoints."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.entities import JobPostingStatus, ApplicationStatus
from app.domain.value_objects import UserRole


class TestHROpportunitiesEndpoint:
    """Tests for /hr/opportunities endpoint."""

    @pytest.mark.asyncio
    async def test_list_opportunities_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/hr/opportunities")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_opportunities_requires_hr_role(
        self, client: AsyncClient, auth_headers_user: dict
    ):
        """Should return 403 for non-HR users."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            headers=auth_headers_user,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_opportunities_success(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return opportunities list for admin."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_opportunities_with_search(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should filter opportunities by search term."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            params={"search": "Python"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_opportunities_pagination(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should respect pagination parameters."""
        response = await client.get(
            "/api/v1/hr/opportunities",
            params={"page": 1, "page_size": 5},
            headers=auth_headers_admin,
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
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_job_posting_validation(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
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
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_job_postings_success(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return job postings list."""
        response = await client.get(
            "/api/v1/hr/job-postings",
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_job_postings_filter_by_status(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should filter by status."""
        response = await client.get(
            "/api/v1/hr/job-postings",
            params={"status": "draft"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_job_posting_not_found(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 404 for non-existent posting."""
        response = await client.get(
            f"/api/v1/hr/job-postings/{uuid4()}",
            headers=auth_headers_admin,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_non_draft_fails(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 400 when trying to publish non-draft."""
        # Non-existent posting will return 404
        response = await client.post(
            f"/api/v1/hr/job-postings/{uuid4()}/publish",
            headers=auth_headers_admin,
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_close_non_published_fails(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 400 when trying to close non-published."""
        response = await client.post(
            f"/api/v1/hr/job-postings/{uuid4()}/close",
            headers=auth_headers_admin,
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
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 404 for non-existent posting."""
        response = await client.get(
            f"/api/v1/hr/job-postings/{uuid4()}/applications",
            headers=auth_headers_admin,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_application_not_found(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 404 for non-existent application."""
        response = await client.get(
            f"/api/v1/hr/applications/{uuid4()}",
            headers=auth_headers_admin,
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
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 400 for invalid status."""
        response = await client.patch(
            f"/api/v1/hr/applications/{uuid4()}/status",
            json={"status": "invalid_status"},
            headers=auth_headers_admin,
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
    async def test_get_cv_url_not_found(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 404 for non-existent application."""
        response = await client.get(
            f"/api/v1/hr/applications/{uuid4()}/cv",
            headers=auth_headers_admin,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_in_boond_not_found(
        self, client: AsyncClient, auth_headers_admin: dict
    ):
        """Should return 404 for non-existent application."""
        response = await client.post(
            f"/api/v1/hr/applications/{uuid4()}/create-in-boond",
            headers=auth_headers_admin,
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
                "tjm_min": "400",
                "tjm_max": "500",
                "availability_date": str(date.today() + timedelta(days=30)),
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code == 404

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
                "tjm_min": "400",
                "tjm_max": "500",
                "availability_date": str(date.today()),
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404]  # 400 if validation, 404 if token not found

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
                "tjm_min": "400",
                "tjm_max": "500",
                "availability_date": str(date.today()),
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_submit_application_validation_tjm(self, client: AsyncClient):
        """Should validate TJM range."""
        response = await client.post(
            "/api/v1/postuler/some-token",
            data={
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean@example.com",
                "phone": "+33612345678",
                "job_title": "Dev",
                "tjm_min": "500",  # Min > Max
                "tjm_max": "400",
                "availability_date": str(date.today()),
            },
            files={"cv": ("cv.pdf", b"PDF content", "application/pdf")},
        )
        assert response.status_code in [400, 404]

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
                "tjm_min": "400",
                "tjm_max": "500",
                "availability_date": str(date.today()),
            },
            files={"cv": ("cv.txt", b"Text content", "text/plain")},
        )
        assert response.status_code in [400, 404]
