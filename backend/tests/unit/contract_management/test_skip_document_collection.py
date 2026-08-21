"""Tests for skipping the vigilance document collection (saisie en personne)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.skip_document_collection import (
    DEFAULT_SKIP_REASON,
    SkipDocumentCollectionUseCase,
)
from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
    ValidateCommercialUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "manual",
        "status": ContractRequestStatus.COLLECTING_DOCUMENTS,
        "third_party_type": "freelance",
        "third_party_id": uuid4(),
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


def _make_doc(status: DocumentStatus, s3_key: str | None = None) -> VigilanceDocument:
    """Create a vigilance document in a given state."""
    return VigilanceDocument(
        third_party_id=uuid4(),
        document_type=DocumentType.KBIS,
        status=status,
        s3_key=s3_key,
    )


def _make_use_case(cr: ContractRequest, documents: list | None = None, **overrides):
    """Build the use case with mocked repositories."""
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=cr)
    cr_repo.save = AsyncMock(side_effect=lambda x: x)

    doc_repo = AsyncMock()
    doc_repo.list_by_third_party = AsyncMock(return_value=documents or [])
    doc_repo.delete = AsyncMock(return_value=True)

    defaults = {
        "contract_request_repository": cr_repo,
        "document_repository": doc_repo,
        "third_party_repository": AsyncMock(),
        "request_documents_use_case": AsyncMock(),
    }
    defaults.update(overrides)
    uc = SkipDocumentCollectionUseCase(**defaults)
    return uc, defaults


class TestSkipDocumentCollection:
    """Skipping the collection unblocks the draft without soliciting the tiers."""

    @pytest.mark.asyncio
    async def test_skip_moves_to_reviewing_compliance_with_traced_override(self):
        """COLLECTING_DOCUMENTS → REVIEWING_COMPLIANCE with a traced justification."""
        cr = _make_cr()
        uc, _ = _make_use_case(cr)

        result = await uc.execute(cr.id, reason="Documents déjà reçus par courrier.")

        assert result.documents_skipped is True
        assert result.compliance_override is True
        assert result.compliance_override_reason == "Documents déjà reçus par courrier."
        assert result.status == ContractRequestStatus.REVIEWING_COMPLIANCE

    @pytest.mark.asyncio
    async def test_skip_without_reason_uses_default_justification(self):
        """A blank reason still leaves a traceable justification."""
        cr = _make_cr()
        uc, _ = _make_use_case(cr)

        result = await uc.execute(cr.id, reason="   ")

        assert result.compliance_override_reason == DEFAULT_SKIP_REASON

    @pytest.mark.asyncio
    async def test_skip_purges_untouched_slots_only(self):
        """Empty slots are removed; anything actually deposited is kept."""
        untouched = _make_doc(DocumentStatus.REQUESTED)
        received = _make_doc(DocumentStatus.RECEIVED, s3_key="s3://kbis.pdf")
        validated = _make_doc(DocumentStatus.VALIDATED, s3_key="s3://rib.pdf")
        cr = _make_cr()
        uc, deps = _make_use_case(cr, documents=[untouched, received, validated])

        await uc.execute(cr.id, reason="Vigilance traitée hors Bobby.")

        deleted_ids = [call.args[0] for call in deps["document_repository"].delete.call_args_list]
        assert deleted_ids == [untouched.id]

    @pytest.mark.asyncio
    async def test_skip_from_compliance_blocked_keeps_status(self):
        """A blocked request is unblocked in place (draft generation already allowed)."""
        cr = _make_cr(status=ContractRequestStatus.COMPLIANCE_BLOCKED)
        uc, _ = _make_use_case(cr)

        result = await uc.execute(cr.id, reason="Dérogation direction.")

        assert result.documents_skipped is True
        assert result.status == ContractRequestStatus.COMPLIANCE_BLOCKED
        assert result.status.can_transition_to(ContractRequestStatus.DRAFT_GENERATED)

    @pytest.mark.asyncio
    async def test_skip_rejected_after_draft_generation(self):
        """Too late once the draft exists — the collection is no longer in play."""
        cr = _make_cr(status=ContractRequestStatus.DRAFT_GENERATED)
        uc, _ = _make_use_case(cr)

        with pytest.raises(InvalidContractStatusError):
            await uc.execute(cr.id, reason="Trop tard.")

    @pytest.mark.asyncio
    async def test_skip_unknown_request_raises(self):
        """An unknown contract request is reported as such."""
        cr = _make_cr()
        uc, deps = _make_use_case(cr)
        deps["contract_request_repository"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ContractRequestNotFoundError):
            await uc.execute(uuid4(), reason="Inconnu.")

    @pytest.mark.asyncio
    async def test_skip_without_document_repository(self):
        """Skipping still works when no document repository is wired."""
        cr = _make_cr()
        uc, _ = _make_use_case(cr, document_repository=None)

        result = await uc.execute(cr.id, reason="Sans dépôt documentaire.")

        assert result.documents_skipped is True


class TestRestoreDocumentCollection:
    """Restoring puts the request back into a normal collection."""

    @pytest.mark.asyncio
    async def test_restore_clears_override_and_returns_to_collecting(self):
        """The traced override is cleared and the request collects again."""
        cr = _make_cr(status=ContractRequestStatus.REVIEWING_COMPLIANCE)
        cr.documents_skipped = True
        cr.compliance_override = True
        cr.compliance_override_reason = DEFAULT_SKIP_REASON
        uc, _ = _make_use_case(cr)

        result = await uc.execute(cr.id, restore=True)

        assert result.documents_skipped is False
        assert result.compliance_override is False
        assert result.compliance_override_reason is None
        assert result.status == ContractRequestStatus.COLLECTING_DOCUMENTS

    @pytest.mark.asyncio
    async def test_restore_recreates_slots_from_entity_category(self):
        """Document slots are re-requested using the tiers' entity category."""
        cr = _make_cr(status=ContractRequestStatus.REVIEWING_COMPLIANCE)
        cr.documents_skipped = True
        tp = AsyncMock()
        tp.id = cr.third_party_id
        tp.entity_category = "societe"
        tp_repo = AsyncMock()
        tp_repo.get_by_id = AsyncMock(return_value=tp)
        request_documents_uc = AsyncMock()
        request_documents_uc.execute = AsyncMock(return_value=[_make_doc(DocumentStatus.REQUESTED)])
        uc, _ = _make_use_case(
            cr, third_party_repository=tp_repo, request_documents_use_case=request_documents_uc
        )

        await uc.execute(cr.id, restore=True)

        request_documents_uc.execute.assert_awaited_once_with(
            cr.third_party_id, entity_category="societe"
        )

    @pytest.mark.asyncio
    async def test_restore_without_entity_category_skips_slot_creation(self):
        """Without the tiers' identity there is nothing to re-request yet."""
        cr = _make_cr(status=ContractRequestStatus.REVIEWING_COMPLIANCE)
        cr.documents_skipped = True
        tp = AsyncMock()
        tp.id = cr.third_party_id
        tp.entity_category = None
        tp_repo = AsyncMock()
        tp_repo.get_by_id = AsyncMock(return_value=tp)
        request_documents_uc = AsyncMock()
        uc, _ = _make_use_case(
            cr, third_party_repository=tp_repo, request_documents_use_case=request_documents_uc
        )

        result = await uc.execute(cr.id, restore=True)

        request_documents_uc.execute.assert_not_awaited()
        assert result.documents_skipped is False


class TestValidateCommercialSkipDocuments:
    """The skip can be decided upfront, at commercial validation."""

    def _use_case(self, cr: ContractRequest, documents: list | None = None):
        cr_repo = AsyncMock()
        cr_repo.get_by_id = AsyncMock(return_value=cr)
        cr_repo.save = AsyncMock(side_effect=lambda x: x)

        tp_repo = AsyncMock()
        tp_repo.get_by_id = AsyncMock(return_value=None)
        tp_repo.save = AsyncMock(side_effect=lambda x: x)

        magic_link_uc = AsyncMock()
        doc_repo = AsyncMock()
        doc_repo.list_by_third_party = AsyncMock(return_value=documents or [])
        doc_repo.delete = AsyncMock(return_value=True)

        uc = ValidateCommercialUseCase(
            contract_request_repository=cr_repo,
            third_party_repository=tp_repo,
            find_or_create_third_party_use_case=None,
            generate_magic_link_use_case=magic_link_uc,
            request_documents_use_case=AsyncMock(),
            document_repository=doc_repo,
        )
        return uc, magic_link_uc, doc_repo

    @pytest.mark.asyncio
    async def test_skip_documents_reaches_reviewing_compliance_without_email(self):
        """No collection email, no collection step: straight to compliance review."""
        cr = _make_cr(
            status=ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION, third_party_id=None
        )
        uc, magic_link_uc, _ = self._use_case(cr)

        result = await uc.execute(
            ValidateCommercialCommand(
                contract_request_id=cr.id,
                third_party_type="freelance",
                contact_email="contact@fournisseur.fr",
                notify_third_party=False,
                skip_documents=True,
            )
        )

        magic_link_uc.execute.assert_not_awaited()
        assert result.documents_skipped is True
        assert result.compliance_override is True
        assert result.status == ContractRequestStatus.REVIEWING_COMPLIANCE
        # The stub ThirdParty is still created — the contract needs its identity.
        assert result.third_party_id is not None

    @pytest.mark.asyncio
    async def test_without_skip_documents_collection_still_happens(self):
        """Default behaviour is unchanged: the request collects documents."""
        cr = _make_cr(
            status=ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION, third_party_id=None
        )
        uc, _, _ = self._use_case(cr)

        result = await uc.execute(
            ValidateCommercialCommand(
                contract_request_id=cr.id,
                third_party_type="freelance",
                contact_email="contact@fournisseur.fr",
                notify_third_party=False,
            )
        )

        assert result.documents_skipped is False
        assert result.compliance_override is False
        assert result.status == ContractRequestStatus.COLLECTING_DOCUMENTS

    @pytest.mark.asyncio
    async def test_skip_documents_never_applies_to_payfit_redirect(self):
        """A salarié goes to PayFit — the skip must not touch that path."""
        cr = _make_cr(
            status=ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION, third_party_id=None
        )
        uc, _, _ = self._use_case(cr)

        result = await uc.execute(
            ValidateCommercialCommand(
                contract_request_id=cr.id,
                third_party_type="salarie",
                contact_email="contact@fournisseur.fr",
                notify_third_party=False,
                skip_documents=True,
            )
        )

        assert result.status == ContractRequestStatus.REDIRECTED_PAYFIT
        assert result.documents_skipped is False


class TestCommercialValidationSchema:
    """The API refuses an incoherent combination of flags."""

    def test_skip_documents_requires_manual_entry(self):
        """Skipping while still emailing the tiers is rejected."""
        from pydantic import ValidationError

        from app.contract_management.api.schemas import CommercialValidationRequest

        with pytest.raises(ValidationError):
            CommercialValidationRequest(
                third_party_type="freelance",
                contact_email="contact@fournisseur.fr",
                notify_third_party=True,
                skip_documents=True,
            )

    def test_skip_documents_accepted_with_manual_entry(self):
        """The manual-entry combination is valid."""
        from app.contract_management.api.schemas import CommercialValidationRequest

        body = CommercialValidationRequest(
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
            notify_third_party=False,
            skip_documents=True,
        )

        assert body.skip_documents is True

    def test_defaults_keep_the_collection(self):
        """Nothing changes for callers that don't opt in."""
        from app.contract_management.api.schemas import CommercialValidationRequest

        body = CommercialValidationRequest(
            third_party_type="freelance",
            contact_email="contact@fournisseur.fr",
        )

        assert body.notify_third_party is True
        assert body.skip_documents is False
