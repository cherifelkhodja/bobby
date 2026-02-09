"""Tests for domain entities."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.entities import Candidate, Cooptation, Opportunity, User
from app.domain.value_objects import CooptationStatus, Email, UserRole


class TestUser:
    """Tests for User entity."""

    def test_create_user(self):
        user = User(
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
            password_hash="hashed_password",
        )
        assert user.email == Email("test@example.com")
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.role == UserRole.USER
        assert not user.is_verified

    def test_full_name(self):
        user = User(
            email=Email("test@example.com"),
            first_name="Jean",
            last_name="Dupont",
        )
        assert user.full_name == "Jean Dupont"

    def test_verify_email(self):
        user = User(
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
            verification_token="token123",
        )
        user.verify_email()
        assert user.is_verified
        assert user.verification_token is None

    def test_is_admin(self):
        admin = User(
            email=Email("admin@example.com"),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        )
        assert admin.is_admin

    def test_reset_token_valid(self):
        user = User(
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
        )
        expires = datetime.utcnow() + timedelta(hours=1)
        user.set_reset_token("reset_token", expires)
        assert user.is_reset_token_valid()

    def test_reset_token_expired(self):
        user = User(
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
        )
        expires = datetime.utcnow() - timedelta(hours=1)
        user.set_reset_token("reset_token", expires)
        assert not user.is_reset_token_valid()


class TestCandidate:
    """Tests for Candidate entity."""

    def test_create_candidate(self):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email=Email("jean.dupont@example.com"),
        )
        assert candidate.first_name == "Jean"
        assert candidate.last_name == "Dupont"
        assert candidate.civility == "M"

    def test_full_name(self):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email=Email("jean.dupont@example.com"),
        )
        assert candidate.full_name == "Jean Dupont"

    def test_display_name(self):
        candidate = Candidate(
            first_name="Marie",
            last_name="Martin",
            email=Email("marie.martin@example.com"),
            civility="Mme",
        )
        assert candidate.display_name == "Mme Marie Martin"


class TestOpportunity:
    """Tests for Opportunity entity."""

    def test_create_opportunity(self):
        opp = Opportunity(
            title="Développeur Python",
            reference="REF-001",
            external_id="12345",
        )
        assert opp.title == "Développeur Python"
        assert opp.is_active

    def test_is_open_with_future_deadline(self):
        from datetime import date

        opp = Opportunity(
            title="Test",
            reference="REF-001",
            external_id="12345",
            response_deadline=date.today() + timedelta(days=7),
        )
        assert opp.is_open

    def test_is_closed_with_past_deadline(self):
        from datetime import date

        opp = Opportunity(
            title="Test",
            reference="REF-001",
            external_id="12345",
            response_deadline=date.today() - timedelta(days=1),
        )
        assert not opp.is_open


class TestCooptation:
    """Tests for Cooptation entity."""

    def test_create_cooptation(self):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email=Email("jean@example.com"),
        )
        opportunity = Opportunity(
            title="Dev Python",
            reference="REF-001",
            external_id="12345",
        )
        submitter_id = uuid4()

        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=submitter_id,
        )

        assert cooptation.status == CooptationStatus.PENDING
        assert cooptation.is_pending
        assert not cooptation.is_final

    def test_change_status_valid_transition(self):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email=Email("jean@example.com"),
        )
        opportunity = Opportunity(
            title="Dev Python",
            reference="REF-001",
            external_id="12345",
        )
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=uuid4(),
        )

        success = cooptation.change_status(CooptationStatus.IN_REVIEW)
        assert success
        assert cooptation.status == CooptationStatus.IN_REVIEW
        assert len(cooptation.status_history) == 1

    def test_change_status_invalid_transition(self):
        candidate = Candidate(
            first_name="Jean",
            last_name="Dupont",
            email=Email("jean@example.com"),
        )
        opportunity = Opportunity(
            title="Dev Python",
            reference="REF-001",
            external_id="12345",
        )
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=uuid4(),
        )

        # Cannot go directly from PENDING to ACCEPTED
        success = cooptation.change_status(CooptationStatus.ACCEPTED)
        assert not success
        assert cooptation.status == CooptationStatus.PENDING
