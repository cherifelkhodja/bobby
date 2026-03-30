"""Use case: Create a purchase order for a purchase_order_only contract request.

This is the fast path when a supplier already has an active framework contract.
Instead of going through the full contract lifecycle, we only verify compliance
and create a purchase order in Bobby + Boond.
"""

from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class CreatePurchaseOrderCommand:
    """Command data for creating a purchase order."""

    def __init__(self, *, contract_request_id: UUID) -> None:
        self.contract_request_id = contract_request_id


class CreatePurchaseOrderUseCase:
    """Create a purchase order for a fast-path contract request.

    Prerequisites:
    - Contract request must be purchase_order_only type
    - Framework contract must be linked and active
    - Third party compliance should be verified
    """

    def __init__(
        self,
        contract_request_repository,
        framework_contract_repository,
        purchase_order_repository,
        third_party_repository,
        crm_service=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._fc_repo = framework_contract_repository
        self._po_repo = purchase_order_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service

    async def execute(self, command: CreatePurchaseOrderCommand) -> PurchaseOrder:
        """Execute the use case.

        Creates a PurchaseOrder in Bobby and optionally in Boond,
        then transitions the contract request to ARCHIVED.
        """
        cr = await self._cr_repo.get_by_id(command.contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(command.contract_request_id))

        if not cr.is_purchase_order_only or not cr.framework_contract_id:
            raise ValueError(
                "Cette demande n'est pas de type bon de commande uniquement."
            )

        fc = await self._fc_repo.get_by_id(cr.framework_contract_id)
        if not fc or not fc.is_usable:
            raise ValueError(
                "Le contrat cadre associé n'est pas actif."
            )

        # Generate purchase order reference
        po_ref = await self._po_repo.get_next_reference(fc.reference)

        po = PurchaseOrder(
            framework_contract_id=fc.id,
            contract_request_id=cr.id,
            reference=po_ref,
            boond_positioning_id=cr.boond_positioning_id,
            consultant_first_name=cr.consultant_first_name,
            consultant_last_name=cr.consultant_last_name,
            daily_rate=cr.daily_rate,
            start_date=cr.start_date,
            end_date=cr.end_date,
            quantity=cr.quantity_sold,
        )

        # Create in Boond if CRM service is available
        tp = await self._tp_repo.get_by_id(fc.third_party_id)
        if self._crm and tp and tp.boond_provider_id and cr.daily_rate:
            try:
                boond_po_id = await self._crm.create_purchase_order(
                    provider_id=tp.boond_provider_id,
                    positioning_id=cr.boond_positioning_id,
                    reference=po_ref,
                    amount=float(cr.daily_rate),
                )
                po.boond_purchase_order_id = boond_po_id
                po.mark_active()
                logger.info(
                    "purchase_order_created_in_boond",
                    cr_id=str(cr.id),
                    po_ref=po_ref,
                    boond_po_id=boond_po_id,
                )
            except Exception as exc:
                logger.warning(
                    "purchase_order_boond_creation_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )
        else:
            po.mark_active()

        saved_po = await self._po_repo.save(po)

        # Transition contract request to ARCHIVED
        if cr.status != ContractRequestStatus.ARCHIVED:
            cr.transition_to(ContractRequestStatus.ARCHIVED)
            await self._cr_repo.save(cr)

        logger.info(
            "purchase_order_created",
            cr_id=str(cr.id),
            po_id=str(saved_po.id),
            po_ref=po_ref,
            framework_contract_ref=fc.reference,
        )
        return saved_po
