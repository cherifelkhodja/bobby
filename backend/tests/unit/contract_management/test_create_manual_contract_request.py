"""Tests for CreateManualContractRequestUseCase."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.contract_management.application.use_cases.create_manual_contract_request import (
    CreateManualContractRequestUseCase,
    ManualContractRequestCommand,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _cr_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_next_provisional_reference = AsyncMock(return_value="PROV-2026-0007")
    repo.save = AsyncMock(side_effect=lambda cr: cr)
    return repo


@pytest.mark.asyncio
async def test_creates_manual_cr_without_crm():
    """Should create a manual CR in pending_commercial_validation without Boond."""
    repo = _cr_repo()
    uc = CreateManualContractRequestUseCase(contract_request_repository=repo, crm_service=None)

    cr = await uc.execute(
        ManualContractRequestCommand(
            boond_resource_id=4242,
            commercial_email="adv@gem.fr",
            consultant_first_name="Jean",
        )
    )

    assert cr.trigger_type == "manual"
    assert cr.boond_resource_id == 4242
    assert cr.boond_consultant_type == "resource"
    assert cr.provisional_reference == "PROV-2026-0007"
    assert cr.status == ContractRequestStatus.PENDING_COMMERCIAL_VALIDATION
    assert cr.commercial_email == "adv@gem.fr"
    assert cr.consultant_first_name == "Jean"


@pytest.mark.asyncio
async def test_enriches_consultant_and_commercial_from_boond():
    """Should enrich consultant from the resource and commercial from its manager."""
    repo = _cr_repo()
    crm = AsyncMock()
    crm.get_candidate_info = AsyncMock(
        return_value={
            "civility": "Mme",
            "first_name": "Marie",
            "last_name": "Curie",
            "email": "marie@x.fr",
            "phone": "+33600000000",
            "manager_id": 99,
        }
    )
    user_repo = AsyncMock()
    user_repo.get_by_boond_resource_id = AsyncMock(
        return_value=SimpleNamespace(email="manager@gem.fr")
    )

    uc = CreateManualContractRequestUseCase(
        contract_request_repository=repo,
        crm_service=crm,
        user_repository=user_repo,
    )

    cr = await uc.execute(
        ManualContractRequestCommand(boond_resource_id=4242, commercial_email="adv@gem.fr")
    )

    crm.get_candidate_info.assert_awaited_once_with(4242, "resource")
    assert cr.consultant_civility == "Mme"
    assert cr.consultant_first_name == "Marie"
    assert cr.consultant_last_name == "Curie"
    assert cr.consultant_email == "marie@x.fr"
    # Commercial resolved from the resource's manager
    assert cr.commercial_email == "manager@gem.fr"


@pytest.mark.asyncio
async def test_boond_lookup_failure_does_not_block_creation():
    """A Boond lookup error must not block creation; provided values are kept."""
    repo = _cr_repo()
    crm = AsyncMock()
    crm.get_candidate_info = AsyncMock(side_effect=RuntimeError("boond down"))

    uc = CreateManualContractRequestUseCase(contract_request_repository=repo, crm_service=crm)

    cr = await uc.execute(
        ManualContractRequestCommand(
            boond_resource_id=4242,
            commercial_email="adv@gem.fr",
            consultant_first_name="Jean",
        )
    )

    assert cr.boond_resource_id == 4242
    assert cr.consultant_first_name == "Jean"
    assert cr.commercial_email == "adv@gem.fr"
