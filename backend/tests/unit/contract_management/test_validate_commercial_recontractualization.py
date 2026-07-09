"""Tests for ValidateCommercialUseCase re-contractualization vigilance.

Verrouille le correctif « docs vides ne saute plus la vigilance » :
pour une recontractualisation (trigger_type=ressource_4), un tiers SANS aucun
document (repo docs -> []) ne doit PAS auto-valider la conformité. Le statut va
vers COLLECTING_DOCUMENTS (collecte), jamais directement REVIEWING_COMPLIANCE.

Ces cas complètent (sans les recréer) ceux de
`test_validate_commercial_simplified.py`.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
    ValidateCommercialUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.vigilance.domain.value_objects.document_status import DocumentStatus


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "candidat_11",
        "status": ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION,
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


def _make_recontractualization_use_case(cr, previous_cr, docs, *, magic_link_uc=None):
    """Build a use case for a ressource_4 re-contractualization flow.

    - cr_repo.get_by_id resolves both the current CR and the previous CR.
    - document_repository.list_by_third_party returns the provided docs.
    """
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(side_effect=lambda id_: cr if id_ == cr.id else previous_cr)
    cr_repo.save = AsyncMock(side_effect=lambda x: x)
    cr_repo.get_by_positioning_id = AsyncMock(return_value=None)

    doc_repo = AsyncMock()
    doc_repo.list_by_third_party = AsyncMock(return_value=docs)

    if magic_link_uc is None:
        magic_link_uc = AsyncMock()
        magic_link_uc.execute = AsyncMock()

    uc = ValidateCommercialUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=AsyncMock(),
        find_or_create_third_party_use_case=None,
        generate_magic_link_use_case=magic_link_uc,
        request_documents_use_case=AsyncMock(),
        document_repository=doc_repo,
    )
    return uc, cr_repo, doc_repo, magic_link_uc


def _command(cr) -> ValidateCommercialCommand:
    return ValidateCommercialCommand(
        contract_request_id=cr.id,
        third_party_type="freelance",
        contact_email="contact@fournisseur.fr",
    )


class TestEmptyDocumentsDoNotSkipVigilance:
    """The core fix: an empty document list must NOT auto-validate compliance."""

    @pytest.mark.asyncio
    async def test_empty_documents_goes_to_collecting(self):
        """No document on the reused ThirdParty -> COLLECTING_DOCUMENTS."""
        previous_tp_id = uuid4()
        previous_cr_id = uuid4()
        previous_cr = _make_cr(
            id=previous_cr_id,
            third_party_id=previous_tp_id,
            status=ContractRequestStatus.ARCHIVED,
        )
        cr = _make_cr(
            trigger_type="ressource_4",
            previous_contract_request_id=previous_cr_id,
        )

        uc, _cr_repo, doc_repo, magic_link_uc = _make_recontractualization_use_case(
            cr, previous_cr, docs=[]
        )

        result = await uc.execute(_command(cr))

        # ThirdParty réutilisé depuis la CR précédente
        assert result.third_party_id == previous_tp_id
        # Vigilance NON sautée : on collecte, on ne passe pas en review
        assert result.status == ContractRequestStatus.COLLECTING_DOCUMENTS
        assert result.status != ContractRequestStatus.REVIEWING_COMPLIANCE
        # Magic link envoyé pour (re)collecter les documents manquants
        magic_link_uc.execute.assert_awaited_once()
        doc_repo.list_by_third_party.assert_awaited_once_with(previous_tp_id)


class TestAllValidDocumentsSkipToReview:
    """Contrast: only genuinely-valid documents skip to compliance review."""

    @pytest.mark.asyncio
    async def test_valid_documents_reach_reviewing_compliance(self):
        """A validated, non-expired document lets the flow reach review."""
        previous_tp_id = uuid4()
        previous_cr_id = uuid4()
        previous_cr = _make_cr(
            id=previous_cr_id,
            third_party_id=previous_tp_id,
            status=ContractRequestStatus.ARCHIVED,
        )
        cr = _make_cr(
            trigger_type="ressource_4",
            previous_contract_request_id=previous_cr_id,
        )

        valid_doc = MagicMock()
        valid_doc.status = DocumentStatus.VALIDATED
        valid_doc.expires_at = datetime.utcnow() + timedelta(days=365)

        uc, _cr_repo, _doc_repo, magic_link_uc = _make_recontractualization_use_case(
            cr, previous_cr, docs=[valid_doc]
        )

        result = await uc.execute(_command(cr))

        assert result.third_party_id == previous_tp_id
        # Tous les documents valides -> saut jusqu'à la revue de conformité
        assert result.status == ContractRequestStatus.REVIEWING_COMPLIANCE
        # Aucun besoin de recollecte -> pas de magic link
        magic_link_uc.execute.assert_not_called()
