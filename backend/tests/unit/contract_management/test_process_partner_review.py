"""Tests for ProcessPartnerReviewUseCase.

Verrouille :
- la garde d'idempotence : une décision ne peut être enregistrée que depuis
  DRAFT_SENT_TO_PARTNER ; tout autre statut lève InvalidContractStatusError
  (rejeu) au lieu de tenter une transition illégale (qui remonterait en 500) ;
- happy path "approved" : transition -> PARTNER_APPROVED + assignation de la
  référence définitive (get_company_code/get_next_reference) + email commercial ;
- "changes requested" : transition -> PARTNER_REQUESTED_CHANGES + commentaires.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.process_partner_review import (
    ProcessPartnerReviewUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity (default: sent to partner)."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "candidat_11",
        "status": ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
        "commercial_email": "commercial@example.com",
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


def _make_use_case(cr: ContractRequest, **overrides) -> ProcessPartnerReviewUseCase:
    """Create use case with mock dependencies and a pre-loaded CR."""
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=cr)
    cr_repo.save = AsyncMock(side_effect=lambda x: x)
    cr_repo.get_company_code = AsyncMock(return_value="GEM")
    cr_repo.get_next_reference = AsyncMock(return_value="GEM-CC-0001")

    contract_repo = AsyncMock()
    contract_repo.get_by_request_id = AsyncMock(return_value=None)
    contract_repo.save = AsyncMock()

    email_service = AsyncMock()
    email_service.send_contract_progress_to_commercial = AsyncMock()

    defaults = {
        "contract_request_repository": cr_repo,
        "contract_repository": contract_repo,
        "email_service": email_service,
        "draft_regenerator": None,
        "company_email_resolver": None,
    }
    defaults.update(overrides)
    return ProcessPartnerReviewUseCase(**defaults)


class TestIdempotenceGuard:
    """Only DRAFT_SENT_TO_PARTNER can receive a partner decision."""

    @pytest.mark.parametrize(
        "status",
        [
            ContractRequestStatus.PARTNER_APPROVED,
            ContractRequestStatus.PARTNER_REQUESTED_CHANGES,
            ContractRequestStatus.DRAFT_GENERATED,
            ContractRequestStatus.SIGNED,
            ContractRequestStatus.CANCELLED,
        ],
    )
    @pytest.mark.asyncio
    async def test_rejects_non_sent_status(self, status):
        """A replay from any non-sent status raises instead of transitioning."""
        cr = _make_cr(status=status)
        uc = _make_use_case(cr)

        with pytest.raises(InvalidContractStatusError):
            await uc.execute(cr.id, approved=True)

        # Aucune transition, aucune sauvegarde : rejet propre
        assert cr.status == status
        uc._cr_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_replay_on_changes_requested(self):
        """approved=False replay is also rejected from a non-sent status."""
        cr = _make_cr(status=ContractRequestStatus.PARTNER_REQUESTED_CHANGES)
        uc = _make_use_case(cr)

        with pytest.raises(InvalidContractStatusError):
            await uc.execute(cr.id, approved=False, comments="rejeu")

        uc._cr_repo.save.assert_not_called()


class TestApproved:
    """Happy path: partner approves the draft."""

    @pytest.mark.asyncio
    async def test_transitions_and_assigns_final_reference(self):
        """Approval transitions to PARTNER_APPROVED and assigns the final ref."""
        company_id = uuid4()
        cr = _make_cr(company_id=company_id, reference=None)
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, approved=True)

        assert result.status == ContractRequestStatus.PARTNER_APPROVED
        # Référence définitive assignée depuis le code société
        assert result.reference == "GEM-CC-0001"
        uc._cr_repo.get_company_code.assert_awaited_once_with(company_id)
        uc._cr_repo.get_next_reference.assert_awaited_once_with("GEM")
        # Email de progression au commercial
        uc._email_service.send_contract_progress_to_commercial.assert_awaited_once()
        call = uc._email_service.send_contract_progress_to_commercial.call_args
        assert call.kwargs["to"] == "commercial@example.com"

    @pytest.mark.asyncio
    async def test_keeps_existing_final_reference(self):
        """An already-final reference (non PROV-) is not regenerated."""
        cr = _make_cr(company_id=uuid4(), reference="GEM-CC-0042")
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, approved=True)

        assert result.reference == "GEM-CC-0042"
        uc._cr_repo.get_next_reference.assert_not_called()

    @pytest.mark.asyncio
    async def test_regenerates_draft_when_regenerator_provided(self):
        """The draft is regenerated with the final reference when possible."""
        regenerator = AsyncMock()
        regenerator.regenerate = AsyncMock()
        cr = _make_cr(company_id=uuid4(), reference=None)
        uc = _make_use_case(cr, draft_regenerator=regenerator)

        result = await uc.execute(cr.id, approved=True)

        regenerator.regenerate.assert_awaited_once_with(result)


class TestChangesRequested:
    """Partner requests changes."""

    @pytest.mark.asyncio
    async def test_transitions_to_requested_changes(self):
        """Rejection transitions to PARTNER_REQUESTED_CHANGES."""
        cr = _make_cr()
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, approved=False, comments="Corriger l'article 3")

        assert result.status == ContractRequestStatus.PARTNER_REQUESTED_CHANGES
        # Le commentaire est attaché à la dernière entrée d'historique
        assert result.status_history[-1]["comment"] == "Corriger l'article 3"
        uc._email_service.send_contract_progress_to_commercial.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_saves_partner_comments_on_contract(self):
        """Partner comments are persisted on the linked contract when present."""
        contract = MagicMock()
        contract_repo = AsyncMock()
        contract_repo.get_by_request_id = AsyncMock(return_value=contract)
        contract_repo.save = AsyncMock()

        cr = _make_cr()
        uc = _make_use_case(cr, contract_repository=contract_repo)

        await uc.execute(cr.id, approved=False, comments="Ajouter une clause RGPD")

        assert contract.partner_comments == "Ajouter une clause RGPD"
        contract_repo.save.assert_awaited_once_with(contract)


class TestInternalRecipients:
    """L'émetteur interne (ADV/admin) est notifié en plus du commercial."""

    @pytest.mark.asyncio
    async def test_approved_notifies_commercial_and_internal_recipients(self):
        """Approval sends the progress email to commercial + ADV/admin issuers."""
        cr = _make_cr(company_id=uuid4(), reference=None)
        uc = _make_use_case(cr, internal_recipients=["adv@example.com", "admin@example.com"])

        await uc.execute(cr.id, approved=True)

        calls = uc._email_service.send_contract_progress_to_commercial.call_args_list
        recipients = [c.kwargs["to"] for c in calls]
        assert recipients == [
            "commercial@example.com",
            "adv@example.com",
            "admin@example.com",
        ]

    @pytest.mark.asyncio
    async def test_changes_requested_notifies_internal_recipients(self):
        """Changes requested also notifies the internal issuers."""
        cr = _make_cr()
        uc = _make_use_case(cr, internal_recipients=["adv@example.com"])

        await uc.execute(cr.id, approved=False, comments="Corriger le TJM")

        calls = uc._email_service.send_contract_progress_to_commercial.call_args_list
        recipients = [c.kwargs["to"] for c in calls]
        assert recipients == ["commercial@example.com", "adv@example.com"]

    @pytest.mark.asyncio
    async def test_recipients_are_deduplicated_and_empty_skipped(self):
        """Commercial appearing in the internal list is only notified once;
        a missing commercial_email does not produce an empty recipient."""
        cr = _make_cr(commercial_email=None)
        uc = _make_use_case(cr, internal_recipients=["adv@example.com", "adv@example.com"])

        await uc.execute(cr.id, approved=False, comments="doublon")

        calls = uc._email_service.send_contract_progress_to_commercial.call_args_list
        recipients = [c.kwargs["to"] for c in calls]
        assert recipients == ["adv@example.com"]


class TestNotFound:
    """Missing contract request raises the domain error."""

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        """Unknown ID raises ContractRequestNotFoundError before any transition."""
        cr_repo = AsyncMock()
        cr_repo.get_by_id = AsyncMock(return_value=None)
        cr_repo.save = AsyncMock()
        uc = _make_use_case(_make_cr(), contract_request_repository=cr_repo)

        with pytest.raises(ContractRequestNotFoundError):
            await uc.execute(uuid4(), approved=True)

        cr_repo.save.assert_not_called()
