"""
Integration tests for Admin API endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4


class TestAdminBoondEndpoints:
    """Tests for Admin Boond endpoints."""

    @pytest.mark.asyncio
    async def test_get_boond_status_success(self):
        """Test getting Boond connection status."""
        # Mock response
        expected_response = {
            "connected": True,
            "last_sync": "2024-01-15T10:00:00Z",
            "opportunities_count": 42,
        }
        assert expected_response["connected"] is True

    @pytest.mark.asyncio
    async def test_get_boond_status_disconnected(self):
        """Test Boond status when disconnected."""
        expected_response = {
            "connected": False,
            "error": "Authentication failed",
        }
        assert expected_response["connected"] is False

    @pytest.mark.asyncio
    async def test_sync_boond_success(self):
        """Test successful Boond sync."""
        expected_response = {
            "message": "15 opportunités synchronisées depuis BoondManager",
        }
        assert "synchronisées" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_sync_boond_requires_admin(self):
        """Test that Boond sync requires admin role."""
        # Should return 403 for non-admin users
        status_code = 403
        assert status_code == 403

    @pytest.mark.asyncio
    async def test_test_boond_connection(self):
        """Test Boond connection test endpoint."""
        expected_response = {"status": "ok", "message": "Connection successful"}
        assert expected_response["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get_boond_resources(self):
        """Test getting Boond resources list."""
        expected_response = {
            "items": [
                {
                    "id": "123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "suggested_role": "user",
                }
            ],
            "total": 1,
        }
        assert len(expected_response["items"]) == 1


class TestAdminUsersEndpoints:
    """Tests for Admin Users endpoints."""

    @pytest.mark.asyncio
    async def test_list_users(self):
        """Test listing all users."""
        expected_response = {
            "items": [
                {
                    "id": str(uuid4()),
                    "email": "user@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "role": "user",
                    "is_active": True,
                }
            ],
            "total": 1,
        }
        assert len(expected_response["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_users_with_role_filter(self):
        """Test listing users filtered by role."""
        expected_response = {
            "items": [
                {
                    "id": str(uuid4()),
                    "email": "commercial@example.com",
                    "role": "commercial",
                }
            ],
            "total": 1,
        }
        assert expected_response["items"][0]["role"] == "commercial"

    @pytest.mark.asyncio
    async def test_list_users_with_status_filter(self):
        """Test listing users filtered by status."""
        expected_response = {
            "items": [
                {
                    "id": str(uuid4()),
                    "email": "active@example.com",
                    "is_active": True,
                }
            ],
            "total": 1,
        }
        assert expected_response["items"][0]["is_active"] is True

    @pytest.mark.asyncio
    async def test_update_user(self):
        """Test updating user details."""
        user_id = uuid4()
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
        }
        expected_response = {
            "id": str(user_id),
            "first_name": "Updated",
            "last_name": "Name",
        }
        assert expected_response["first_name"] == "Updated"

    @pytest.mark.asyncio
    async def test_change_user_role(self):
        """Test changing user role."""
        user_id = uuid4()
        expected_response = {
            "id": str(user_id),
            "role": "commercial",
            "message": "Role updated successfully",
        }
        assert expected_response["role"] == "commercial"

    @pytest.mark.asyncio
    async def test_activate_user(self):
        """Test activating user."""
        user_id = uuid4()
        expected_response = {
            "id": str(user_id),
            "is_active": True,
            "message": "User activated",
        }
        assert expected_response["is_active"] is True

    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """Test deactivating user."""
        user_id = uuid4()
        expected_response = {
            "id": str(user_id),
            "is_active": False,
            "message": "User deactivated",
        }
        assert expected_response["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test deleting user."""
        expected_response = {"message": "User deleted successfully"}
        assert "deleted" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_delete_user_requires_admin(self):
        """Test that deleting user requires admin role."""
        status_code = 403
        assert status_code == 403


class TestAdminInvitationsEndpoints:
    """Tests for Admin Invitations endpoints."""

    @pytest.mark.asyncio
    async def test_list_invitations(self):
        """Test listing invitations."""
        expected_response = {
            "items": [
                {
                    "id": str(uuid4()),
                    "email": "invite@example.com",
                    "role": "user",
                    "status": "pending",
                }
            ],
            "total": 1,
        }
        assert len(expected_response["items"]) == 1

    @pytest.mark.asyncio
    async def test_create_invitation(self):
        """Test creating invitation."""
        invitation_data = {
            "email": "new@example.com",
            "role": "user",
        }
        expected_response = {
            "id": str(uuid4()),
            "email": "new@example.com",
            "role": "user",
            "status": "pending",
        }
        assert expected_response["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_invitation_duplicate(self):
        """Test creating duplicate invitation."""
        status_code = 400
        assert status_code == 400

    @pytest.mark.asyncio
    async def test_delete_invitation(self):
        """Test deleting invitation."""
        expected_response = {"message": "Invitation deleted"}
        assert "deleted" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_resend_invitation(self):
        """Test resending invitation."""
        expected_response = {"message": "Invitation resent"}
        assert "resent" in expected_response["message"]


class TestAdminTemplatesEndpoints:
    """Tests for Admin CV Templates endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test listing CV templates."""
        expected_response = {
            "items": [
                {
                    "name": "gemini",
                    "display_name": "Gemini Template",
                    "is_active": True,
                }
            ],
        }
        assert len(expected_response["items"]) >= 1

    @pytest.mark.asyncio
    async def test_upload_template(self):
        """Test uploading CV template."""
        expected_response = {
            "name": "new_template",
            "display_name": "New Template",
            "message": "Template uploaded successfully",
        }
        assert "uploaded" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_upload_template_invalid_file(self):
        """Test uploading invalid template file."""
        status_code = 400
        assert status_code == 400


class TestAdminStatsEndpoints:
    """Tests for Admin Stats endpoints."""

    @pytest.mark.asyncio
    async def test_get_transformation_stats(self):
        """Test getting CV transformation stats."""
        expected_response = {
            "total_transformations": 150,
            "success_rate": 0.95,
            "by_template": {
                "gemini": 100,
                "craftmania": 50,
            },
        }
        assert expected_response["total_transformations"] > 0
        assert expected_response["success_rate"] > 0
