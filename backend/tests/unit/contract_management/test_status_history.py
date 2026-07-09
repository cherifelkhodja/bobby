"""Tests for ContractRequest status-history bootstrapping and rollback.

Verrouille le correctif garantissant que ``status_history`` n'est jamais vide :
une entrée initiale est amorcée à la création, ce qui permet à
``rollback_to_previous_status`` de fonctionner dès la première transition
(auparavant impossible faute de statut précédent enregistré).
"""

from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity (mirrors the use-case tests)."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "candidat_11",
        "status": ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION,
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


class TestInitialStatusHistory:
    """The history must be seeded with the starting status at creation."""

    def test_creation_seeds_initial_entry(self):
        """A brand-new request has exactly one initial history entry."""
        cr = _make_cr()

        assert len(cr.status_history) == 1
        entry = cr.status_history[0]
        assert entry["status"] == ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION.value
        assert entry.get("initial") is True
        # The last entry always reflects the current status.
        assert cr.status_history[-1]["status"] == cr.status.value

    def test_reloaded_history_is_not_reseeded(self):
        """An entity rebuilt with a populated history is left untouched."""
        existing = [
            {
                "status": ContractRequestStatus.COMMERCIAL_VALIDATED.value,
                "entered_at": "2026-01-01T00:00:00",
                "initial": True,
            }
        ]
        cr = _make_cr(
            status=ContractRequestStatus.COMMERCIAL_VALIDATED,
            status_history=existing,
        )

        # No duplicate initial entry is appended for the reloaded row.
        assert len(cr.status_history) == 1
        assert cr.status_history[0]["status"] == ContractRequestStatus.COMMERCIAL_VALIDATED.value


class TestTransitionHistory:
    """A legal transition appends a new history entry."""

    def test_transition_appends_entry(self):
        """After one transition the history has two entries, last = current."""
        cr = _make_cr()

        cr.transition_to(ContractRequestStatus.COMMERCIAL_VALIDATED)

        assert len(cr.status_history) == 2
        assert cr.status == ContractRequestStatus.COMMERCIAL_VALIDATED
        assert cr.status_history[-1]["status"] == cr.status.value


class TestRollback:
    """Rollback is possible from the first transition and is non-destructive."""

    def test_rollback_after_first_transition_returns_to_previous(self):
        """Rollback restores the previous status right after one transition.

        Ce cas échouait avant le correctif : sans entrée initiale, l'historique
        ne contenait aucun statut précédent distinct après une seule transition.
        """
        cr = _make_cr()
        cr.transition_to(ContractRequestStatus.COMMERCIAL_VALIDATED)

        cr.rollback_to_previous_status()

        # Reverted to the prior status.
        assert cr.status == ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION
        # Last entry mirrors the current status after rollback.
        assert cr.status_history[-1]["status"] == cr.status.value

    def test_rollback_is_non_destructive(self):
        """Rollback appends an audit entry rather than truncating history."""
        cr = _make_cr()
        cr.transition_to(ContractRequestStatus.COMMERCIAL_VALIDATED)
        len_before = len(cr.status_history)

        cr.rollback_to_previous_status()

        # History grows (audit trail) instead of shrinking.
        assert len(cr.status_history) == len_before + 1
        audit_entry = cr.status_history[-1]
        assert audit_entry.get("rollback") is True
        assert (
            audit_entry.get("rolled_back_from")
            == ContractRequestStatus.COMMERCIAL_VALIDATED.value
        )
        # The original initial entry is preserved at the front.
        assert cr.status_history[0].get("initial") is True
