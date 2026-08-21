"""Choix du contrat cadre applicable à une société émettrice.

Un contrat cadre lie un fournisseur à **une** société du groupe : celui signé
avec l'une ne couvre pas les missions émises par une autre.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    ContractRequestRepository,
)

GEMINI = uuid4()
LEONUM = uuid4()


def _framework(company_id, reference) -> ContractRequest:
    return ContractRequest(
        provisional_reference=reference,
        reference=reference,
        status=ContractRequestStatus.ACTIVE,
        company_id=company_id,
    )


def _repo(frameworks: list[ContractRequest]) -> ContractRequestRepository:
    """Dépôt dont seule la sélection est testée, la requête étant simulée."""
    repo = ContractRequestRepository(session=AsyncMock())
    repo.list_framework_contracts_for_third_party = AsyncMock(return_value=frameworks)
    return repo


class TestFrameworkScoping:
    @pytest.mark.asyncio
    async def test_picks_the_framework_of_the_requested_company(self):
        gemini = _framework(GEMINI, "GEM-CC-003")
        leonum = _framework(LEONUM, "LEO-CC-001")
        repo = _repo([leonum, gemini])

        found = await repo.get_framework_contract_for_third_party(uuid4(), GEMINI)

        assert found.reference == "GEM-CC-003"

    @pytest.mark.asyncio
    async def test_a_framework_with_another_company_does_not_count(self):
        """Le cas signalé : sous contrat avec l'une, rien avec l'autre."""
        repo = _repo([_framework(GEMINI, "GEM-CC-003")])

        assert await repo.get_framework_contract_for_third_party(uuid4(), LEONUM) is None

    @pytest.mark.asyncio
    async def test_without_a_company_the_most_recent_wins(self):
        """Sans société précisée, on renseigne sur l'existence d'un cadre."""
        repo = _repo([_framework(LEONUM, "LEO-CC-001"), _framework(GEMINI, "GEM-CC-003")])

        found = await repo.get_framework_contract_for_third_party(uuid4())

        assert found.reference == "LEO-CC-001"

    @pytest.mark.asyncio
    async def test_a_legacy_framework_without_company_serves_as_fallback(self):
        """Les dossiers antérieurs au multi-sociétés restent exploitables."""
        repo = _repo([_framework(None, "GEN-CC-007")])

        found = await repo.get_framework_contract_for_third_party(uuid4(), LEONUM)

        assert found.reference == "GEN-CC-007"

    @pytest.mark.asyncio
    async def test_an_exact_match_beats_the_legacy_fallback(self):
        repo = _repo([_framework(None, "GEN-CC-007"), _framework(LEONUM, "LEO-CC-001")])

        found = await repo.get_framework_contract_for_third_party(uuid4(), LEONUM)

        assert found.reference == "LEO-CC-001"

    @pytest.mark.asyncio
    async def test_a_supplier_without_any_framework(self):
        repo = _repo([])

        assert await repo.get_framework_contract_for_third_party(uuid4(), GEMINI) is None


class TestFrameworkCoversThePurchaseOrder:
    """Garde-fou d'envoi en signature : le cadre doit couvrir la mission."""

    def _po(self, company_id) -> PurchaseOrder:
        return PurchaseOrder(reference="GEM-BC-001", company_id=company_id)

    def test_a_signed_framework_of_the_same_company_covers(self):
        assert self._po(GEMINI).is_covered_by(_framework(GEMINI, "GEM-CC-003"))

    def test_a_framework_of_another_company_does_not_cover(self):
        """Le cas signalé, vu depuis le bon de commande."""
        assert not self._po(LEONUM).is_covered_by(_framework(GEMINI, "GEM-CC-003"))

    def test_an_unsigned_framework_never_covers(self):
        pending = ContractRequest(
            provisional_reference="PROV-2026-010",
            status=ContractRequestStatus.COLLECTING_DOCUMENTS,
            company_id=GEMINI,
        )
        assert not self._po(GEMINI).is_covered_by(pending)

    def test_no_framework_at_all(self):
        assert not self._po(GEMINI).is_covered_by(None)

    def test_a_legacy_framework_without_company_still_covers(self):
        """L'historique ne doit pas bloquer les dossiers en cours."""
        assert self._po(GEMINI).is_covered_by(_framework(None, "GEN-CC-007"))
