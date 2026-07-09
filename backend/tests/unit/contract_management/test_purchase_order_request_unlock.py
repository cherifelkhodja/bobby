"""Tests for the BDC lock/unlock behaviour on PurchaseOrderRequest."""

from uuid import uuid4

import pytest

from app.contract_management.domain.entities.purchase_order_request import (
    PurchaseOrderRequest,
)
from app.contract_management.domain.exceptions import InvalidContractStatusError
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)


def _locked_por() -> PurchaseOrderRequest:
    return PurchaseOrderRequest(
        boond_positioning_id=433,
        commercial_email="com@example.com",
        reference="GEN-PO-001",
        boond_candidate_id=42,
        status=PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT,
    )


class TestStatusHelpers:
    def test_locked_status_not_editable(self):
        assert PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT.is_editable is False

    def test_pending_validation_editable(self):
        assert PurchaseOrderRequestStatus.PENDING_VALIDATION.is_editable is True

    def test_terminal_not_editable(self):
        assert PurchaseOrderRequestStatus.ARCHIVED.is_editable is False
        assert PurchaseOrderRequestStatus.CANCELLED.is_editable is False

    def test_locked_can_transition_to_validation_or_cancel(self):
        locked = PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT
        assert locked.can_transition_to(PurchaseOrderRequestStatus.PENDING_VALIDATION)
        assert locked.can_transition_to(PurchaseOrderRequestStatus.CANCELLED)
        assert not locked.can_transition_to(PurchaseOrderRequestStatus.ACTIVE)


class TestUnlock:
    def test_unlock_links_framework_and_transitions(self):
        por = _locked_por()
        fc_id = uuid4()
        tp_id = uuid4()

        por.unlock(framework_contract_id=fc_id, third_party_id=tp_id)

        assert por.status == PurchaseOrderRequestStatus.PENDING_VALIDATION
        assert por.framework_contract_id == fc_id
        assert por.third_party_id == tp_id
        assert por.is_editable is True

    def test_unlock_from_wrong_status_raises(self):
        por = _locked_por()
        por.status = PurchaseOrderRequestStatus.ACTIVE

        with pytest.raises(InvalidContractStatusError):
            por.unlock(framework_contract_id=uuid4(), third_party_id=uuid4())
