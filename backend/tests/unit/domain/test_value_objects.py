"""Tests for domain value objects."""

import pytest

from app.domain.exceptions import InvalidEmailError, InvalidPhoneError
from app.domain.value_objects import CooptationStatus, Email, OpportunityStatus, Phone, UserRole


class TestUserRole:
    """Tests for UserRole value object."""

    def test_user_role_values(self):
        """Test all role values exist."""
        assert UserRole.USER.value == "user"
        assert UserRole.COMMERCIAL.value == "commercial"
        assert UserRole.RH.value == "rh"
        assert UserRole.ADMIN.value == "admin"

    def test_user_role_str(self):
        """Test string representation."""
        assert str(UserRole.USER) == "user"
        assert str(UserRole.ADMIN) == "admin"

    def test_display_names(self):
        """Test display names are in French."""
        assert UserRole.USER.display_name == "Utilisateur"
        assert UserRole.COMMERCIAL.display_name == "Commercial"
        assert UserRole.RH.display_name == "RH"
        assert UserRole.ADMIN.display_name == "Administrateur"

    def test_can_manage_users(self):
        """Test user management permissions."""
        assert UserRole.ADMIN.can_manage_users is True
        assert UserRole.RH.can_manage_users is True
        assert UserRole.COMMERCIAL.can_manage_users is False
        assert UserRole.USER.can_manage_users is False

    def test_can_manage_opportunities(self):
        """Test opportunity management permissions."""
        assert UserRole.ADMIN.can_manage_opportunities is True
        assert UserRole.COMMERCIAL.can_manage_opportunities is True
        assert UserRole.RH.can_manage_opportunities is False
        assert UserRole.USER.can_manage_opportunities is False

    def test_can_view_all_cooptations(self):
        """Test cooptation view permissions."""
        assert UserRole.ADMIN.can_view_all_cooptations is True
        assert UserRole.RH.can_view_all_cooptations is True
        assert UserRole.COMMERCIAL.can_view_all_cooptations is False
        assert UserRole.USER.can_view_all_cooptations is False

    def test_can_change_cooptation_status(self):
        """Test cooptation status change permissions."""
        assert UserRole.ADMIN.can_change_cooptation_status is True
        assert UserRole.RH.can_change_cooptation_status is True
        assert UserRole.COMMERCIAL.can_change_cooptation_status is True
        assert UserRole.USER.can_change_cooptation_status is False


class TestCooptationStatus:
    """Tests for CooptationStatus value object."""

    def test_status_values(self):
        """Test all status values exist."""
        assert CooptationStatus.PENDING.value == "pending"
        assert CooptationStatus.IN_REVIEW.value == "in_review"
        assert CooptationStatus.INTERVIEW.value == "interview"
        assert CooptationStatus.ACCEPTED.value == "accepted"
        assert CooptationStatus.REJECTED.value == "rejected"

    def test_is_final(self):
        """Test final status identification."""
        assert CooptationStatus.PENDING.is_final is False
        assert CooptationStatus.IN_REVIEW.is_final is False
        assert CooptationStatus.INTERVIEW.is_final is False
        assert CooptationStatus.ACCEPTED.is_final is True
        assert CooptationStatus.REJECTED.is_final is True

    def test_display_names_french(self):
        """Test display names are in French."""
        assert CooptationStatus.PENDING.display_name == "En attente"
        assert CooptationStatus.IN_REVIEW.display_name == "En cours d'examen"
        assert CooptationStatus.INTERVIEW.display_name == "En entretien"
        assert CooptationStatus.ACCEPTED.display_name == "Accepté"
        assert CooptationStatus.REJECTED.display_name == "Refusé"

    def test_valid_transitions_from_pending(self):
        """Test valid transitions from PENDING status."""
        pending = CooptationStatus.PENDING
        assert pending.can_transition_to(CooptationStatus.IN_REVIEW) is True
        assert pending.can_transition_to(CooptationStatus.REJECTED) is True
        assert pending.can_transition_to(CooptationStatus.INTERVIEW) is False
        assert pending.can_transition_to(CooptationStatus.ACCEPTED) is False
        assert pending.can_transition_to(CooptationStatus.PENDING) is False

    def test_valid_transitions_from_in_review(self):
        """Test valid transitions from IN_REVIEW status."""
        in_review = CooptationStatus.IN_REVIEW
        assert in_review.can_transition_to(CooptationStatus.INTERVIEW) is True
        assert in_review.can_transition_to(CooptationStatus.ACCEPTED) is True
        assert in_review.can_transition_to(CooptationStatus.REJECTED) is True
        assert in_review.can_transition_to(CooptationStatus.PENDING) is False
        assert in_review.can_transition_to(CooptationStatus.IN_REVIEW) is False

    def test_valid_transitions_from_interview(self):
        """Test valid transitions from INTERVIEW status."""
        interview = CooptationStatus.INTERVIEW
        assert interview.can_transition_to(CooptationStatus.ACCEPTED) is True
        assert interview.can_transition_to(CooptationStatus.REJECTED) is True
        assert interview.can_transition_to(CooptationStatus.PENDING) is False
        assert interview.can_transition_to(CooptationStatus.IN_REVIEW) is False
        assert interview.can_transition_to(CooptationStatus.INTERVIEW) is False

    def test_no_transitions_from_accepted(self):
        """Test no valid transitions from ACCEPTED status."""
        accepted = CooptationStatus.ACCEPTED
        assert accepted.can_transition_to(CooptationStatus.PENDING) is False
        assert accepted.can_transition_to(CooptationStatus.IN_REVIEW) is False
        assert accepted.can_transition_to(CooptationStatus.INTERVIEW) is False
        assert accepted.can_transition_to(CooptationStatus.REJECTED) is False
        assert accepted.can_transition_to(CooptationStatus.ACCEPTED) is False

    def test_no_transitions_from_rejected(self):
        """Test no valid transitions from REJECTED status."""
        rejected = CooptationStatus.REJECTED
        assert rejected.can_transition_to(CooptationStatus.PENDING) is False
        assert rejected.can_transition_to(CooptationStatus.IN_REVIEW) is False
        assert rejected.can_transition_to(CooptationStatus.INTERVIEW) is False
        assert rejected.can_transition_to(CooptationStatus.ACCEPTED) is False
        assert rejected.can_transition_to(CooptationStatus.REJECTED) is False


class TestOpportunityStatus:
    """Tests for OpportunityStatus value object."""

    def test_status_values(self):
        """Test all status values exist."""
        assert OpportunityStatus.DRAFT.value == "draft"
        assert OpportunityStatus.PUBLISHED.value == "published"
        assert OpportunityStatus.CLOSED.value == "closed"

    def test_display_names_french(self):
        """Test display names are in French."""
        assert OpportunityStatus.DRAFT.display_name == "Brouillon"
        assert OpportunityStatus.PUBLISHED.display_name == "Publiée"
        assert OpportunityStatus.CLOSED.display_name == "Clôturée"

    def test_is_visible_to_consultants(self):
        """Test visibility to consultants."""
        assert OpportunityStatus.DRAFT.is_visible_to_consultants is False
        assert OpportunityStatus.PUBLISHED.is_visible_to_consultants is True
        assert OpportunityStatus.CLOSED.is_visible_to_consultants is False


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        """Test valid email creation."""
        email = Email("test@example.com")
        assert str(email) == "test@example.com"

    def test_email_equality_case_insensitive(self):
        """Test email equality is case-insensitive."""
        email1 = Email("Test@Example.COM")
        email2 = Email("test@example.com")
        assert email1 == email2

    def test_invalid_email_missing_at(self):
        """Test invalid email without @ symbol."""
        with pytest.raises(InvalidEmailError):
            Email("invalid-email")

    def test_invalid_email_missing_domain(self):
        """Test invalid email without domain."""
        with pytest.raises(InvalidEmailError):
            Email("test@")

    def test_invalid_email_empty(self):
        """Test invalid empty email."""
        with pytest.raises(InvalidEmailError):
            Email("")


class TestPhone:
    """Tests for Phone value object."""

    def test_valid_phone_french_mobile(self):
        """Test valid French mobile number."""
        phone = Phone("+33612345678")
        assert str(phone) == "+33612345678"

    def test_valid_phone_with_spaces(self):
        """Test phone number with spaces is normalized."""
        phone = Phone("+33 6 12 34 56 78")
        assert str(phone) == "+33612345678"

    def test_valid_phone_with_dots(self):
        """Test phone number with dots is normalized."""
        phone = Phone("+33.6.12.34.56.78")
        assert str(phone) == "+33612345678"

    def test_valid_phone_national_format(self):
        """Test valid French national format."""
        phone = Phone("0612345678")
        assert str(phone) == "0612345678"

    def test_invalid_phone_too_short(self):
        """Test invalid phone number too short."""
        with pytest.raises(InvalidPhoneError):
            Phone("+331")

    def test_phone_equality(self):
        """Test phone equality comparison."""
        phone1 = Phone("+33612345678")
        phone2 = Phone("+33 6 12 34 56 78")
        assert phone1 == phone2
