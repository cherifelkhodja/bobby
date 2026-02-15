"""Tests for DocumentStatus state machine transitions."""

import pytest

from app.vigilance.domain.value_objects.document_status import DocumentStatus


class TestDocumentStatusTransitions:
    """Tests for valid and invalid status transitions."""

    def test_requested_can_transition_to_received(self):
        """Given REQUESTED, it can transition to RECEIVED."""
        assert DocumentStatus.REQUESTED.can_transition_to(DocumentStatus.RECEIVED)

    def test_requested_cannot_transition_to_validated(self):
        """Given REQUESTED, it cannot skip to VALIDATED."""
        assert not DocumentStatus.REQUESTED.can_transition_to(DocumentStatus.VALIDATED)

    def test_received_can_transition_to_validated(self):
        """Given RECEIVED, it can transition to VALIDATED."""
        assert DocumentStatus.RECEIVED.can_transition_to(DocumentStatus.VALIDATED)

    def test_received_can_transition_to_rejected(self):
        """Given RECEIVED, it can transition to REJECTED."""
        assert DocumentStatus.RECEIVED.can_transition_to(DocumentStatus.REJECTED)

    def test_validated_can_transition_to_expiring_soon(self):
        """Given VALIDATED, it can transition to EXPIRING_SOON."""
        assert DocumentStatus.VALIDATED.can_transition_to(DocumentStatus.EXPIRING_SOON)

    def test_validated_cannot_transition_to_requested(self):
        """Given VALIDATED, it cannot go back to REQUESTED directly."""
        assert not DocumentStatus.VALIDATED.can_transition_to(DocumentStatus.REQUESTED)

    def test_rejected_can_transition_to_requested(self):
        """Given REJECTED, it can re-request the document."""
        assert DocumentStatus.REJECTED.can_transition_to(DocumentStatus.REQUESTED)

    def test_expired_can_transition_to_requested(self):
        """Given EXPIRED, it can re-request the document."""
        assert DocumentStatus.EXPIRED.can_transition_to(DocumentStatus.REQUESTED)

    def test_expiring_soon_can_transition_to_expired(self):
        """Given EXPIRING_SOON, it can transition to EXPIRED."""
        assert DocumentStatus.EXPIRING_SOON.can_transition_to(DocumentStatus.EXPIRED)

    def test_expiring_soon_can_be_revalidated(self):
        """Given EXPIRING_SOON, it can transition back to VALIDATED."""
        assert DocumentStatus.EXPIRING_SOON.can_transition_to(DocumentStatus.VALIDATED)
