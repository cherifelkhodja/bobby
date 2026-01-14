"""Tests for domain value objects."""

import pytest

from app.domain.exceptions import InvalidEmailError, InvalidPhoneError
from app.domain.value_objects import CooptationStatus, Email, Phone, UserRole


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        email = Email("test@example.com")
        assert str(email) == "test@example.com"

    def test_invalid_email_raises_error(self):
        with pytest.raises(InvalidEmailError):
            Email("invalid-email")

    def test_email_equality_case_insensitive(self):
        email1 = Email("Test@Example.com")
        email2 = Email("test@example.com")
        assert email1 == email2

    def test_email_domain(self):
        email = Email("user@geminiconsulting.fr")
        assert email.domain == "geminiconsulting.fr"

    def test_email_local_part(self):
        email = Email("user@geminiconsulting.fr")
        assert email.local_part == "user"


class TestPhone:
    """Tests for Phone value object."""

    def test_valid_french_phone(self):
        phone = Phone("0612345678")
        assert str(phone) == "0612345678"

    def test_valid_french_international_phone(self):
        phone = Phone("+33612345678")
        assert str(phone) == "+33612345678"

    def test_phone_normalizes_spaces(self):
        phone = Phone("06 12 34 56 78")
        assert str(phone) == "0612345678"

    def test_invalid_phone_raises_error(self):
        with pytest.raises(InvalidPhoneError):
            Phone("123")

    def test_phone_formatted(self):
        phone = Phone("0612345678")
        assert phone.formatted == "06 12 34 56 78"


class TestCooptationStatus:
    """Tests for CooptationStatus enum."""

    def test_pending_can_transition_to_in_review(self):
        status = CooptationStatus.PENDING
        assert status.can_transition_to(CooptationStatus.IN_REVIEW)

    def test_pending_can_transition_to_rejected(self):
        status = CooptationStatus.PENDING
        assert status.can_transition_to(CooptationStatus.REJECTED)

    def test_accepted_is_final(self):
        status = CooptationStatus.ACCEPTED
        assert status.is_final

    def test_rejected_is_final(self):
        status = CooptationStatus.REJECTED
        assert status.is_final

    def test_final_status_cannot_transition(self):
        status = CooptationStatus.ACCEPTED
        assert not status.can_transition_to(CooptationStatus.PENDING)

    def test_display_name(self):
        status = CooptationStatus.PENDING
        assert status.display_name == "En attente"


class TestUserRole:
    """Tests for UserRole enum."""

    def test_user_role(self):
        role = UserRole.USER
        assert str(role) == "user"

    def test_admin_role(self):
        role = UserRole.ADMIN
        assert str(role) == "admin"
