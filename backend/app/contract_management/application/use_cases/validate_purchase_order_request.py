"""Use case: Validate commercial data for a purchase order request."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)

logger = structlog.get_logger()


class ValidatePurchaseOrderRequestCommand:
    """Command data for validating a purchase order request."""

    def __init__(
        self,
        *,
        purchase_order_request_id: UUID,
        daily_rate: Decimal,
        start_date: date,
        end_date: date | None = None,
        quantity_sold: int | None = None,
        client_name: str | None = None,
        mission_title: str | None = None,
        consultant_civility: str | None = None,
        consultant_first_name: str | None = None,
        consultant_last_name: str | None = None,
        consultant_email: str | None = None,
        consultant_phone: str | None = None,
    ) -> None:
        self.purchase_order_request_id = purchase_order_request_id
        self.daily_rate = daily_rate
        self.start_date = start_date
        self.end_date = end_date
        self.quantity_sold = quantity_sold
        self.client_name = client_name
        self.mission_title = mission_title
        self.consultant_civility = consultant_civility
        self.consultant_first_name = consultant_first_name
        self.consultant_last_name = consultant_last_name
        self.consultant_email = consultant_email
        self.consultant_phone = consultant_phone


class ValidatePurchaseOrderRequestUseCase:
    """Apply commercial validation to a purchase order request.

    This is the simplified validation for BDC requests (no third_party_type,
    no document collection — those are handled by the framework contract).
    """

    def __init__(self, purchase_order_request_repository) -> None:
        self._por_repo = purchase_order_request_repository

    async def execute(self, command: ValidatePurchaseOrderRequestCommand):
        por = await self._por_repo.get_by_id(command.purchase_order_request_id)
        if not por:
            raise ContractRequestNotFoundError(str(command.purchase_order_request_id))

        por.validate(
            daily_rate=command.daily_rate,
            start_date=command.start_date,
            end_date=command.end_date,
            quantity_sold=command.quantity_sold,
            client_name=command.client_name,
            mission_title=command.mission_title,
        )

        # Apply consultant fields
        if command.consultant_civility is not None:
            por.consultant_civility = command.consultant_civility
        if command.consultant_first_name is not None:
            por.consultant_first_name = command.consultant_first_name
        if command.consultant_last_name is not None:
            por.consultant_last_name = command.consultant_last_name
        if command.consultant_email is not None:
            por.consultant_email = command.consultant_email
        if command.consultant_phone is not None:
            por.consultant_phone = command.consultant_phone

        # Automatically transition to checking compliance
        por.transition_to(PurchaseOrderRequestStatus.CHECKING_COMPLIANCE)

        saved = await self._por_repo.save(por)
        logger.info(
            "purchase_order_request_validated",
            por_id=str(saved.id),
            reference=saved.reference,
        )
        return saved
