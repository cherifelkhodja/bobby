"""Tests for ApproveDraftInternallyUseCase (ADV approves on partner's behalf)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.approve_draft_internally import (
    ApproveDraftInternallyUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _cr(status: ContractRequestStatus, **kw) -> ContractRequest:
    return ContractRequest(provisional_reference="PROV-2026-0001", status=status, **kw)


def _repo(cr: ContractRequest) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=cr)
    repo.get_company_code = AsyncMock(return_value="GEM")
    repo.get_next_reference = AsyncMock(return_value="GEM-CC-0001")
    repo.save = AsyncMock(side_effect=lambda c: c)
    return repo


@pytest.mark.asyncio
async def test_approve_from_draft_generated_assigns_reference_and_regenerates():
    cr = _cr(ContractRequestStatus.DRAFT_GENERATED, company_id=uuid4())
    repo = _repo(cr)
    regen = AsyncMock()

    uc = ApproveDraftInternallyUseCase(contract_request_repository=repo, draft_regenerator=regen)
    result = await uc.execute(cr.id)

    assert result.status == ContractRequestStatus.PARTNER_APPROVED
    assert result.reference == "GEM-CC-0001"
    regen.regenerate.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_from_draft_sent_to_partner():
    cr = _cr(ContractRequestStatus.DRAFT_SENT_TO_PARTNER, company_id=uuid4())
    repo = _repo(cr)

    uc = ApproveDraftInternallyUseCase(contract_request_repository=repo)
    result = await uc.execute(cr.id)

    assert result.status == ContractRequestStatus.PARTNER_APPROVED


@pytest.mark.asyncio
async def test_invalid_status_raises():
    cr = _cr(ContractRequestStatus.COLLECTING_DOCUMENTS)
    repo = _repo(cr)

    uc = ApproveDraftInternallyUseCase(contract_request_repository=repo)
    with pytest.raises(InvalidContractStatusError):
        await uc.execute(cr.id)


@pytest.mark.asyncio
async def test_not_found_raises():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)

    uc = ApproveDraftInternallyUseCase(contract_request_repository=repo)
    with pytest.raises(ContractRequestNotFoundError):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_keeps_existing_definitive_reference():
    cr = _cr(ContractRequestStatus.DRAFT_GENERATED, reference="GEM-CC-0009", company_id=uuid4())
    repo = _repo(cr)

    uc = ApproveDraftInternallyUseCase(contract_request_repository=repo)
    result = await uc.execute(cr.id)

    repo.get_next_reference.assert_not_awaited()
    assert result.reference == "GEM-CC-0009"
