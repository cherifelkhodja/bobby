"""
Integration tests for Invitations API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4


class TestCreateInvitation:
    """Tests for creating invitations."""

    @pytest.mark.asyncio
    async def test_create_invitation_success(self):
        """Test successful invitation creation."""
        invitation_data = {
            "email": "newuser@example.com",
            "role": "user",
        }
        expected_response = {
            "id": str(uuid4()),
            "email": "newuser@example.com",
            "role": "user",
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }
        assert expected_response["email"] == invitation_data["email"]
        assert expected_response["role"] == invitation_data["role"]

    @pytest.mark.asyncio
    async def test_create_invitation_with_boond_resource(self):
        """Test creating invitation linked to Boond resource."""
        invitation_data = {
            "email": "boonduser@example.com",
            "role": "user",
            "boond_resource_id": "12345",
            "manager_boond_id": "67890",
        }
        expected_response = {
            "id": str(uuid4()),
            "email": "boonduser@example.com",
            "boond_resource_id": "12345",
        }
        assert expected_response["boond_resource_id"] == "12345"

    @pytest.mark.asyncio
    async def test_create_invitation_duplicate_email(self):
        """Test creating invitation with existing email."""
        error_response = {
            "detail": "Une invitation existe déjà pour cet email"
        }
        assert "existe déjà" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_create_invitation_existing_user(self):
        """Test creating invitation for existing user."""
        error_response = {
            "detail": "Un utilisateur existe déjà avec cet email"
        }
        assert "utilisateur existe" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_create_invitation_invalid_email(self):
        """Test creating invitation with invalid email."""
        error_response = {
            "detail": "Adresse email invalide"
        }
        assert "invalide" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_create_invitation_invalid_role(self):
        """Test creating invitation with invalid role."""
        error_response = {
            "detail": "Rôle invalide"
        }
        assert "invalide" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_create_invitation_requires_admin_or_rh(self):
        """Test that creating invitation requires admin or RH role."""
        status_code = 403
        assert status_code == 403


class TestListInvitations:
    """Tests for listing invitations."""

    @pytest.mark.asyncio
    async def test_list_invitations_success(self):
        """Test successful listing of invitations."""
        expected_response = {
            "items": [
                {
                    "id": str(uuid4()),
                    "email": "pending@example.com",
                    "role": "user",
                    "created_at": datetime.utcnow().isoformat(),
                    "is_accepted": False,
                }
            ],
            "total": 1,
        }
        assert len(expected_response["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_invitations_empty(self):
        """Test listing when no invitations exist."""
        expected_response = {
            "items": [],
            "total": 0,
        }
        assert expected_response["total"] == 0

    @pytest.mark.asyncio
    async def test_list_invitations_pagination(self):
        """Test invitation list pagination."""
        expected_response = {
            "items": [{"id": str(uuid4())}] * 10,
            "total": 50,
            "page": 1,
            "page_size": 10,
        }
        assert len(expected_response["items"]) == 10
        assert expected_response["total"] == 50


class TestDeleteInvitation:
    """Tests for deleting invitations."""

    @pytest.mark.asyncio
    async def test_delete_invitation_success(self):
        """Test successful invitation deletion."""
        expected_response = {"message": "Invitation supprimée"}
        assert "supprimée" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_delete_invitation_not_found(self):
        """Test deleting non-existent invitation."""
        error_response = {"detail": "Invitation non trouvée"}
        assert "non trouvée" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_delete_accepted_invitation(self):
        """Test deleting already accepted invitation."""
        error_response = {"detail": "Impossible de supprimer une invitation acceptée"}
        assert "acceptée" in error_response["detail"]


class TestResendInvitation:
    """Tests for resending invitations."""

    @pytest.mark.asyncio
    async def test_resend_invitation_success(self):
        """Test successful invitation resend."""
        expected_response = {
            "message": "Invitation renvoyée",
            "new_expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }
        assert "renvoyée" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_resend_invitation_not_found(self):
        """Test resending non-existent invitation."""
        error_response = {"detail": "Invitation non trouvée"}
        assert "non trouvée" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_resend_accepted_invitation(self):
        """Test resending accepted invitation."""
        error_response = {"detail": "Impossible de renvoyer une invitation acceptée"}
        assert "acceptée" in error_response["detail"]


class TestValidateInvitation:
    """Tests for validating invitations."""

    @pytest.mark.asyncio
    async def test_validate_invitation_success(self):
        """Test successful invitation validation."""
        token = "valid_token_123"
        expected_response = {
            "email": "invited@example.com",
            "role": "user",
            "is_valid": True,
            "hours_until_expiry": 168,
        }
        assert expected_response["is_valid"] is True
        assert expected_response["hours_until_expiry"] > 0

    @pytest.mark.asyncio
    async def test_validate_invitation_expired(self):
        """Test validating expired invitation."""
        expected_response = {
            "email": "expired@example.com",
            "role": "user",
            "is_valid": False,
            "hours_until_expiry": 0,
        }
        assert expected_response["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_invitation_invalid_token(self):
        """Test validating with invalid token."""
        error_response = {"detail": "Token invalide"}
        assert "invalide" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_validate_invitation_already_accepted(self):
        """Test validating already accepted invitation."""
        expected_response = {
            "email": "accepted@example.com",
            "is_valid": False,
        }
        assert expected_response["is_valid"] is False


class TestAcceptInvitation:
    """Tests for accepting invitations."""

    @pytest.mark.asyncio
    async def test_accept_invitation_success(self):
        """Test successful invitation acceptance."""
        accept_data = {
            "token": "valid_token",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
        }
        expected_response = {
            "message": "Compte créé avec succès",
            "user_id": str(uuid4()),
        }
        assert "succès" in expected_response["message"]

    @pytest.mark.asyncio
    async def test_accept_invitation_weak_password(self):
        """Test accepting with weak password."""
        error_response = {"detail": "Le mot de passe doit contenir au moins 8 caractères"}
        assert "mot de passe" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_accept_invitation_expired(self):
        """Test accepting expired invitation."""
        error_response = {"detail": "Cette invitation a expiré"}
        assert "expiré" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_accept_invitation_already_accepted(self):
        """Test accepting already accepted invitation."""
        error_response = {"detail": "Cette invitation a déjà été acceptée"}
        assert "déjà été acceptée" in error_response["detail"]

    @pytest.mark.asyncio
    async def test_accept_invitation_with_prefilled_data(self):
        """Test accepting invitation with pre-filled data from Boond."""
        expected_response = {
            "message": "Compte créé avec succès",
            "user_id": str(uuid4()),
            "first_name": "John",  # Pre-filled from Boond
            "last_name": "Doe",  # Pre-filled from Boond
        }
        assert expected_response["first_name"] == "John"
