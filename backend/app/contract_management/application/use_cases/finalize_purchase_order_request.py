"""Use case: Finalize a purchase order request — create BDC in Bobby + Boond."""

from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)

logger = structlog.get_logger()


class FinalizePurchaseOrderRequestUseCase:
    """Create a PurchaseOrder from a validated PurchaseOrderRequest.

    Checks compliance, creates PO in Bobby and Boond, transitions to ACTIVE.
    """

    def __init__(
        self,
        purchase_order_request_repository,
        framework_contract_repository,
        purchase_order_repository,
        third_party_repository,
        crm_service=None,
    ) -> None:
        self._por_repo = purchase_order_request_repository
        self._fc_repo = framework_contract_repository
        self._po_repo = purchase_order_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service

    async def execute(self, purchase_order_request_id: UUID):
        por = await self._por_repo.get_by_id(purchase_order_request_id)
        if not por:
            raise ContractRequestNotFoundError(str(purchase_order_request_id))

        if por.status not in (
            PurchaseOrderRequestStatus.CHECKING_COMPLIANCE,
            PurchaseOrderRequestStatus.VALIDATED,
        ):
            raise ValueError(
                f"Le BDC ne peut pas être finalisé depuis le statut {por.status.display_name}."
            )

        # Load framework contract
        fc = await self._fc_repo.get_by_id(por.framework_contract_id)
        if not fc or not fc.is_usable:
            raise ValueError("Le contrat cadre associé n'est pas actif.")

        # Check compliance
        tp = await self._tp_repo.get_by_id(fc.third_party_id)
        if tp and tp.compliance_status not in ("compliant", "expiring_soon"):
            por.transition_to(PurchaseOrderRequestStatus.COMPLIANCE_EXPIRED)
            await self._por_repo.save(por)
            raise ValueError(
                "Les documents de conformité du fournisseur ne sont pas à jour. "
                "Veuillez les mettre à jour avant de finaliser le bon de commande."
            )

        # Generate PO reference
        po_ref = await self._po_repo.get_next_reference(fc.reference)

        # Create PurchaseOrder entity
        po = PurchaseOrder(
            framework_contract_id=fc.id,
            contract_request_id=por.original_contract_request_id or por.id,
            reference=po_ref,
            boond_positioning_id=por.boond_positioning_id,
            consultant_first_name=por.consultant_first_name,
            consultant_last_name=por.consultant_last_name,
            daily_rate=por.daily_rate,
            start_date=por.start_date,
            end_date=por.end_date,
            quantity=por.quantity_sold,
        )

        # Create in Boond
        if self._crm and tp and tp.boond_provider_id and por.daily_rate:
            try:
                boond_po_id = await self._crm.create_purchase_order(
                    provider_id=tp.boond_provider_id,
                    positioning_id=por.boond_positioning_id,
                    reference=po_ref,
                    amount=float(por.daily_rate),
                )
                po.boond_purchase_order_id = boond_po_id
                logger.info(
                    "purchase_order_created_in_boond",
                    por_id=str(por.id),
                    po_ref=po_ref,
                    boond_po_id=boond_po_id,
                )
            except Exception as exc:
                logger.warning(
                    "purchase_order_boond_creation_failed",
                    por_id=str(por.id),
                    error=str(exc),
                )

        po.mark_active()
        saved_po = await self._po_repo.save(po)

        # Link PO to POR and transition to ACTIVE
        por.purchase_order_id = saved_po.id
        por.transition_to(PurchaseOrderRequestStatus.ACTIVE)
        await self._por_repo.save(por)

        logger.info(
            "purchase_order_request_finalized",
            por_id=str(por.id),
            po_id=str(saved_po.id),
            po_ref=po_ref,
        )
        return saved_po
