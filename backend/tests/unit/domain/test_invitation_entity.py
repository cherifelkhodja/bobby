"""Tests for Invitation domain entity."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities import Invitation
from app.domain.value_objects import Email, UserRole


def create_invitation(**kwargs) -> Invitation:
    """Factory for creating test invitations."""
    defaults = {
        "email": Email("invited@example.com"),
        "role": UserRole.USER,
        "invited_by": uuid4(),
        "token": "test-token-123",
        "expires_at": datetime.utcnow() + timedelta(hours=48),
    }
    defaults.update(kwargs)
    return Invitation(**defaults)


class TestInvitationCreation:
    """Tests for invitation creation."""

    def test_create_invitation_with_defaults(self):
        """Test creating invitation with default values."""
        invitation = create_invitation()
        
        assert str(invitation.email) == "invited@example.com"
        assert invitation.role == UserRole.USER
        assert invitation.token == "test-token-123"
        assert invitation.accepted_at is None
        assert invitation.id is not None

    def test_create_invitation_with_boond_data(self):
        """Test creating invitation with BoondManager data."""
        invitation = create_invitation(
            boond_resource_id="res-123",
            manager_boond_id="mgr-456",
            phone="+33612345678",
            first_name="John",
            last_name="Doe",
        )
        
        assert invitation.boond_resource_id == "res-123"
        assert invitation.manager_boond_id == "mgr-456"
        assert invitation.phone == "+33612345678"
        assert invitation.first_name == "John"
        assert invitation.last_name == "Doe"

    def test_create_invitation_factory_method(self):
        """Test create() factory method sets expiry correctly."""
        invitation = Invitation.create(
            email=Email("new@example.com"),
            role=UserRole.COMMERCIAL,
            invited_by=uuid4(),
            token="factory-token",
            validity_hours=24,
        )
        
        assert str(invitation.email) == "new@example.com"
        assert invitation.role == UserRole.COMMERCIAL
        # Should expire in approximately 24 hours
        hours_until = invitation.hours_until_expiry
        assert 23 <= hours_until <= 24


class TestInvitationExpiry:
    """Tests for invitation expiry logic."""

    def test_is_expired_false_for_future_expiry(self):
        """Test is_expired returns False for future expiry."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        assert invitation.is_expired is False

    def test_is_expired_true_for_past_expiry(self):
        """Test is_expired returns True for past expiry."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert invitation.is_expired is True

    def test_hours_until_expiry_returns_correct_hours(self):
        """Test hours_until_expiry returns correct value."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() + timedelta(hours=10)
        )
        assert 9 <= invitation.hours_until_expiry <= 10

    def test_hours_until_expiry_returns_zero_when_expired(self):
        """Test hours_until_expiry returns 0 when expired."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=5)
        )
        assert invitation.hours_until_expiry == 0


class TestInvitationAcceptance:
    """Tests for invitation acceptance logic."""

    def test_is_accepted_false_when_not_accepted(self):
        """Test is_accepted returns False when not accepted."""
        invitation = create_invitation()
        assert invitation.is_accepted is False

    def test_is_accepted_true_after_accept(self):
        """Test is_accepted returns True after calling accept()."""
        invitation = create_invitation()
        invitation.accept()
        assert invitation.is_accepted is True

    def test_accept_sets_accepted_at(self):
        """Test accept() sets accepted_at timestamp."""
        invitation = create_invitation()
        before = datetime.utcnow()
        invitation.accept()
        after = datetime.utcnow()
        
        assert invitation.accepted_at is not None
        assert before <= invitation.accepted_at <= after

    def test_accept_raises_when_expired(self):
        """Test accept() raises ValueError when invitation is expired."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        with pytest.raises(ValueError, match="Cannot accept expired invitation"):
            invitation.accept()

    def test_accept_raises_when_already_accepted(self):
        """Test accept() raises ValueError when already accepted."""
        invitation = create_invitation()
        invitation.accept()  # First accept
        
        with pytest.raises(ValueError, match="Invitation already accepted"):
            invitation.accept()  # Second accept should fail


class TestInvitationValidity:
    """Tests for invitation validity logic."""

    def test_is_valid_true_when_not_expired_and_not_accepted(self):
        """Test is_valid returns True for valid invitation."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        assert invitation.is_valid is True

    def test_is_valid_false_when_expired(self):
        """Test is_valid returns False when expired."""
        invitation = create_invitation(
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert invitation.is_valid is False

    def test_is_valid_false_when_accepted(self):
        """Test is_valid returns False when accepted."""
        invitation = create_invitation()
        invitation.accept()
        assert invitation.is_valid is False

    def test_is_valid_false_when_expired_and_accepted(self):
        """Test is_valid returns False when both expired and accepted."""
        invitation = create_invitation()
        invitation.accept()
        # Manually set expiry to past (simulating edge case)
        invitation.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert invitation.is_valid is False
