"""Tests for ContractRequestStatus state machine."""

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

    def test_commercial_validated_cannot_go_to_draft(self):
        """Given COMMERCIAL_VALIDATED, cannot skip to DRAFT_GENERATED."""
        assert not ContractRequestStatus.COMMERCIAL_VALIDATED.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_reviewing_compliance_can_generate_draft(self):
        """Given REVIEWING_COMPLIANCE, can generate draft directly (no CONFIGURING_CONTRACT)."""
        assert ContractRequestStatus.REVIEWING_COMPLIANCE.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_reviewing_compliance_cannot_go_to_configuring(self):
        """Given REVIEWING_COMPLIANCE, cannot go to CONFIGURING_CONTRACT (removed)."""
        assert not ContractRequestStatus.REVIEWING_COMPLIANCE.can_transition_to(
            ContractRequestStatus.CONFIGURING_CONTRACT
        )

    def test_compliance_blocked_can_generate_draft(self):
        """Given COMPLIANCE_BLOCKED, can generate draft (with override)."""
        assert ContractRequestStatus.COMPLIANCE_BLOCKED.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_compliance_blocked_can_return_to_collecting(self):
        """Given COMPLIANCE_BLOCKED, can return to collecting documents."""
        assert ContractRequestStatus.COMPLIANCE_BLOCKED.can_transition_to(
            ContractRequestStatus.COLLECTING_DOCUMENTS
        )

    def test_draft_generated_can_send_to_partner(self):
        """Given DRAFT_GENERATED, can send to partner."""
        assert ContractRequestStatus.DRAFT_GENERATED.can_transition_to(
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER
        )

    def test_draft_generated_can_regenerate(self):
        """Given DRAFT_GENERATED, can regenerate (self-transition)."""
        assert ContractRequestStatus.DRAFT_GENERATED.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_draft_generated_cannot_go_to_configuring(self):
        """Given DRAFT_GENERATED, cannot go back to CONFIGURING_CONTRACT (removed)."""
        assert not ContractRequestStatus.DRAFT_GENERATED.can_transition_to(
            ContractRequestStatus.CONFIGURING_CONTRACT
        )

    def test_partner_requested_changes_can_regenerate_draft(self):
        """Given PARTNER_REQUESTED_CHANGES, can regenerate draft directly."""
        assert ContractRequestStatus.PARTNER_REQUESTED_CHANGES.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_partner_requested_changes_cannot_go_to_configuring(self):
        """Given PARTNER_REQUESTED_CHANGES, cannot go to CONFIGURING_CONTRACT (removed)."""
        assert not ContractRequestStatus.PARTNER_REQUESTED_CHANGES.can_transition_to(
            ContractRequestStatus.CONFIGURING_CONTRACT
        )

    def test_partner_approved_can_go_to_signature(self):
        """Given PARTNER_APPROVED, can go to signature."""
        assert ContractRequestStatus.PARTNER_APPROVED.can_transition_to(
            ContractRequestStatus.SENT_FOR_SIGNATURE
        )

    def test_signed_can_go_to_active(self):
        """Given SIGNED, can go to ACTIVE."""
        assert ContractRequestStatus.SIGNED.can_transition_to(ContractRequestStatus.ACTIVE)

    def test_active_can_be_archived(self):
        """Given ACTIVE, can be archived."""
        assert ContractRequestStatus.ACTIVE.can_transition_to(ContractRequestStatus.ARCHIVED)

    def test_archived_is_terminal(self):
        """Given ARCHIVED, no transitions are allowed."""
        assert not ContractRequestStatus.ARCHIVED.can_transition_to(ContractRequestStatus.SIGNED)
        assert not ContractRequestStatus.ARCHIVED.can_transition_to(ContractRequestStatus.CANCELLED)

    def test_cancelled_is_terminal(self):
        """Given CANCELLED, no transitions are allowed."""
        assert len(ContractRequestStatus.CANCELLED.allowed_transitions) == 0

    def test_any_active_state_can_cancel(self):
        """Most active states should allow cancellation."""
        cancellable = [
            ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION,
            ContractRequestStatus.COMMERCIAL_VALIDATED,
            ContractRequestStatus.COLLECTING_DOCUMENTS,
            ContractRequestStatus.REVIEWING_COMPLIANCE,
            ContractRequestStatus.COMPLIANCE_BLOCKED,
            ContractRequestStatus.DRAFT_GENERATED,
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
            ContractRequestStatus.PARTNER_APPROVED,
            ContractRequestStatus.PARTNER_REQUESTED_CHANGES,
            ContractRequestStatus.SENT_FOR_SIGNATURE,
        ]
        for status in cancellable:
            assert status.can_transition_to(ContractRequestStatus.CANCELLED), (
                f"{status.value} should be cancellable"
            )

    def test_legacy_configuring_contract_can_generate_draft(self):
        """Legacy CONFIGURING_CONTRACT rows can still transition to DRAFT_GENERATED."""
        assert ContractRequestStatus.CONFIGURING_CONTRACT.can_transition_to(
            ContractRequestStatus.DRAFT_GENERATED
        )

    def test_legacy_configuring_contract_can_cancel(self):
        """Legacy CONFIGURING_CONTRACT rows can still be cancelled."""
        assert ContractRequestStatus.CONFIGURING_CONTRACT.can_transition_to(
            ContractRequestStatus.CANCELLED
        )

    def test_display_name_returns_french_labels(self):
        """All statuses should have a display name."""
        for status in ContractRequestStatus:
            assert status.display_name, f"{status.value} has no display_name"
