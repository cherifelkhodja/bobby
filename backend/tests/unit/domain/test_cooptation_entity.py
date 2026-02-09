"""Tests for Cooptation domain entity."""

from uuid import uuid4

from app.domain.entities import Candidate, Cooptation, Opportunity
from app.domain.value_objects import CooptationStatus
from app.domain.value_objects.contact import Email


def create_candidate(**kwargs) -> Candidate:
    """Factory for creating test candidates."""
    defaults = {
        "email": Email("candidate@example.com"),
        "first_name": "John",
        "last_name": "Doe",
        "civility": "M",
    }
    defaults.update(kwargs)
    return Candidate(**defaults)


def create_opportunity(**kwargs) -> Opportunity:
    """Factory for creating test opportunities."""
    defaults = {
        "title": "Test Opportunity",
        "reference": "REF-001",
        "external_id": "ext-123",
        "is_active": True,
        "is_shared": True,
        "owner_id": uuid4(),
    }
    defaults.update(kwargs)
    return Opportunity(**defaults)


def create_cooptation(**kwargs) -> Cooptation:
    """Factory for creating test cooptations."""
    defaults = {
        "candidate": create_candidate(),
        "opportunity": create_opportunity(),
        "submitter_id": uuid4(),
        "status": CooptationStatus.PENDING,
    }
    defaults.update(kwargs)
    return Cooptation(**defaults)


class TestCooptationCreation:
    """Tests for cooptation creation."""

    def test_create_cooptation_with_defaults(self):
        """Test creating cooptation with default values."""
        cooptation = create_cooptation()

        assert cooptation.status == CooptationStatus.PENDING
        assert cooptation.external_positioning_id is None
        assert cooptation.rejection_reason is None
        assert len(cooptation.status_history) == 0
        assert cooptation.id is not None
        assert cooptation.submitted_at is not None
        assert cooptation.updated_at is not None

    def test_cooptation_has_candidate(self):
        """Test cooptation has candidate reference."""
        candidate = create_candidate(first_name="Jane")
        cooptation = create_cooptation(candidate=candidate)

        assert cooptation.candidate.first_name == "Jane"

    def test_cooptation_has_opportunity(self):
        """Test cooptation has opportunity reference."""
        opportunity = create_opportunity(title="Special Opportunity")
        cooptation = create_cooptation(opportunity=opportunity)

        assert cooptation.opportunity.title == "Special Opportunity"


class TestCooptationStatusProperties:
    """Tests for cooptation status properties."""

    def test_is_pending_true(self):
        """Test is_pending returns True for PENDING status."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)
        assert cooptation.is_pending is True

    def test_is_pending_false_for_other_statuses(self):
        """Test is_pending returns False for non-PENDING status."""
        for status in [
            CooptationStatus.IN_REVIEW,
            CooptationStatus.INTERVIEW,
            CooptationStatus.ACCEPTED,
            CooptationStatus.REJECTED,
        ]:
            cooptation = create_cooptation(status=status)
            assert cooptation.is_pending is False, f"Failed for status {status}"

    def test_is_final_true_for_accepted(self):
        """Test is_final returns True for ACCEPTED status."""
        cooptation = create_cooptation(status=CooptationStatus.ACCEPTED)
        assert cooptation.is_final is True

    def test_is_final_true_for_rejected(self):
        """Test is_final returns True for REJECTED status."""
        cooptation = create_cooptation(status=CooptationStatus.REJECTED)
        assert cooptation.is_final is True

    def test_is_final_false_for_non_final_statuses(self):
        """Test is_final returns False for non-final statuses."""
        for status in [
            CooptationStatus.PENDING,
            CooptationStatus.IN_REVIEW,
            CooptationStatus.INTERVIEW,
        ]:
            cooptation = create_cooptation(status=status)
            assert cooptation.is_final is False, f"Failed for status {status}"


class TestCooptationStatusTransitions:
    """Tests for cooptation status transitions."""

    def test_change_status_pending_to_in_review(self):
        """Test valid transition from PENDING to IN_REVIEW."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)
        changed_by = uuid4()

        result = cooptation.change_status(
            new_status=CooptationStatus.IN_REVIEW,
            changed_by=changed_by,
            comment="Starting review",
        )

        assert result is True
        assert cooptation.status == CooptationStatus.IN_REVIEW
        assert len(cooptation.status_history) == 1
        assert cooptation.status_history[0].from_status == CooptationStatus.PENDING
        assert cooptation.status_history[0].to_status == CooptationStatus.IN_REVIEW
        assert cooptation.status_history[0].changed_by == changed_by
        assert cooptation.status_history[0].comment == "Starting review"

    def test_change_status_pending_to_rejected(self):
        """Test valid transition from PENDING to REJECTED."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)

        result = cooptation.change_status(
            new_status=CooptationStatus.REJECTED,
            comment="Not qualified",
        )

        assert result is True
        assert cooptation.status == CooptationStatus.REJECTED
        assert cooptation.rejection_reason == "Not qualified"

    def test_change_status_in_review_to_interview(self):
        """Test valid transition from IN_REVIEW to INTERVIEW."""
        cooptation = create_cooptation(status=CooptationStatus.IN_REVIEW)

        result = cooptation.change_status(new_status=CooptationStatus.INTERVIEW)

        assert result is True
        assert cooptation.status == CooptationStatus.INTERVIEW

    def test_change_status_in_review_to_accepted(self):
        """Test valid transition from IN_REVIEW to ACCEPTED."""
        cooptation = create_cooptation(status=CooptationStatus.IN_REVIEW)

        result = cooptation.change_status(new_status=CooptationStatus.ACCEPTED)

        assert result is True
        assert cooptation.status == CooptationStatus.ACCEPTED

    def test_change_status_interview_to_accepted(self):
        """Test valid transition from INTERVIEW to ACCEPTED."""
        cooptation = create_cooptation(status=CooptationStatus.INTERVIEW)

        result = cooptation.change_status(new_status=CooptationStatus.ACCEPTED)

        assert result is True
        assert cooptation.status == CooptationStatus.ACCEPTED

    def test_change_status_interview_to_rejected(self):
        """Test valid transition from INTERVIEW to REJECTED."""
        cooptation = create_cooptation(status=CooptationStatus.INTERVIEW)

        result = cooptation.change_status(
            new_status=CooptationStatus.REJECTED,
            comment="Failed interview",
        )

        assert result is True
        assert cooptation.status == CooptationStatus.REJECTED
        assert cooptation.rejection_reason == "Failed interview"

    def test_invalid_transition_pending_to_accepted(self):
        """Test invalid transition from PENDING to ACCEPTED fails."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)

        result = cooptation.change_status(new_status=CooptationStatus.ACCEPTED)

        assert result is False
        assert cooptation.status == CooptationStatus.PENDING  # Unchanged
        assert len(cooptation.status_history) == 0

    def test_invalid_transition_pending_to_interview(self):
        """Test invalid transition from PENDING to INTERVIEW fails."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)

        result = cooptation.change_status(new_status=CooptationStatus.INTERVIEW)

        assert result is False
        assert cooptation.status == CooptationStatus.PENDING

    def test_no_transition_from_accepted(self):
        """Test no transitions allowed from ACCEPTED status."""
        cooptation = create_cooptation(status=CooptationStatus.ACCEPTED)

        for target_status in CooptationStatus:
            result = cooptation.change_status(new_status=target_status)
            assert result is False, f"Transition to {target_status} should fail"
            assert cooptation.status == CooptationStatus.ACCEPTED

    def test_no_transition_from_rejected(self):
        """Test no transitions allowed from REJECTED status."""
        cooptation = create_cooptation(status=CooptationStatus.REJECTED)

        for target_status in CooptationStatus:
            result = cooptation.change_status(new_status=target_status)
            assert result is False, f"Transition to {target_status} should fail"
            assert cooptation.status == CooptationStatus.REJECTED

    def test_status_change_updates_timestamp(self):
        """Test status change updates updated_at timestamp."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)
        original_updated = cooptation.updated_at

        cooptation.change_status(new_status=CooptationStatus.IN_REVIEW)

        assert cooptation.updated_at >= original_updated


class TestCooptationStatusHistory:
    """Tests for cooptation status history tracking."""

    def test_status_history_accumulates(self):
        """Test status history accumulates with each change."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)

        cooptation.change_status(new_status=CooptationStatus.IN_REVIEW)
        cooptation.change_status(new_status=CooptationStatus.INTERVIEW)
        cooptation.change_status(new_status=CooptationStatus.ACCEPTED)

        assert len(cooptation.status_history) == 3
        assert cooptation.status_history[0].to_status == CooptationStatus.IN_REVIEW
        assert cooptation.status_history[1].to_status == CooptationStatus.INTERVIEW
        assert cooptation.status_history[2].to_status == CooptationStatus.ACCEPTED

    def test_get_last_status_change_returns_most_recent(self):
        """Test get_last_status_change returns the most recent change."""
        cooptation = create_cooptation(status=CooptationStatus.PENDING)

        cooptation.change_status(new_status=CooptationStatus.IN_REVIEW)
        cooptation.change_status(new_status=CooptationStatus.INTERVIEW)

        last_change = cooptation.get_last_status_change()

        assert last_change is not None
        assert last_change.to_status == CooptationStatus.INTERVIEW

    def test_get_last_status_change_returns_none_if_no_history(self):
        """Test get_last_status_change returns None if no history."""
        cooptation = create_cooptation()

        last_change = cooptation.get_last_status_change()

        assert last_change is None


class TestCooptationExternalIds:
    """Tests for cooptation external ID management."""

    def test_update_external_positioning_id(self):
        """Test updating external positioning ID."""
        cooptation = create_cooptation()
        assert cooptation.external_positioning_id is None

        cooptation.update_external_positioning_id("pos-123")

        assert cooptation.external_positioning_id == "pos-123"

    def test_update_external_positioning_id_updates_timestamp(self):
        """Test updating external ID updates timestamp."""
        cooptation = create_cooptation()
        original_updated = cooptation.updated_at

        cooptation.update_external_positioning_id("pos-123")

        assert cooptation.updated_at >= original_updated
