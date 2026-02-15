"""Tests for ContractRequestStatus state machine."""

import pytest

from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


class TestContractRequestStatusTransitions:
    """Tests for valid and invalid status transitions."""

    def test_pending_can_transition_to_commercial_validated(self):
        """Given PENDING, can transition to COMMERCIAL_VALIDATED."""
        assert ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION.can_transition_to(
            ContractRequestStatus.COMMERCIAL_VALIDATED
        )

    def test_pending_can_transition_to_redirected_payfit(self):
        """Given PENDING, can redirect to PayFit."""
        assert ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION.can_transition_to(
            ContractRequestStatus.REDIRECTED_PAYFIT
        )

    def test_pending_cannot_skip_to_signed(self):
        """Given PENDING, cannot skip to SIGNED."""
        assert not ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION.can_transition_to(
            ContractRequestStatus.SIGNED
        )

    def test_commercial_validated_can_collect_documents(self):
        """Given COMMERCIAL_VALIDATED, can collect documents."""
        assert ContractRequestStatus.COMMERCIAL_VALIDATED.can_transition_to(
            ContractRequestStatus.COLLECTING_DOCUMENTS
        )

    def test_partner_approved_can_go_to_signature(self):
        """Given PARTNER_APPROVED, can go to signature."""
        assert ContractRequestStatus.PARTNER_APPROVED.can_transition_to(
            ContractRequestStatus.SENT_FOR_SIGNATURE
        )

    def test_signed_can_be_archived(self):
        """Given SIGNED, can be archived."""
        assert ContractRequestStatus.SIGNED.can_transition_to(
            ContractRequestStatus.ARCHIVED
        )

    def test_archived_is_terminal(self):
        """Given ARCHIVED, no transitions are allowed."""
        assert not ContractRequestStatus.ARCHIVED.can_transition_to(
            ContractRequestStatus.SIGNED
        )
        assert not ContractRequestStatus.ARCHIVED.can_transition_to(
            ContractRequestStatus.CANCELLED
        )

    def test_cancelled_is_terminal(self):
        """Given CANCELLED, no transitions are allowed."""
        assert len(ContractRequestStatus.CANCELLED.allowed_transitions) == 0

    def test_any_active_state_can_cancel(self):
        """Most active states should allow cancellation."""
        cancellable = [
            ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION,
            ContractRequestStatus.COMMERCIAL_VALIDATED,
            ContractRequestStatus.COLLECTING_DOCUMENTS,
            ContractRequestStatus.CONFIGURING_CONTRACT,
            ContractRequestStatus.DRAFT_GENERATED,
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
            ContractRequestStatus.SENT_FOR_SIGNATURE,
        ]
        for status in cancellable:
            assert status.can_transition_to(ContractRequestStatus.CANCELLED), (
                f"{status.value} should be cancellable"
            )
