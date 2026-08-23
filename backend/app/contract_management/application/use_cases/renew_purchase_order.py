"""Use case: Renew a mission by issuing a new purchase order."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    InvalidPurchaseOrderDataError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

logger = structlog.get_logger()

# Une reconduction part d'une mission qui a réellement eu lieu : un bon de
# commande encore en préparation se corrige, il ne se reconduit pas.
RENEWABLE_STATUSES = frozenset(
    {
        PurchaseOrderStatus.ACTIVE,
        PurchaseOrderStatus.CLOSED,
        PurchaseOrderStatus.SIGNED,
    }
)


@dataclass
class RenewPurchaseOrderCommand:
    """Nouvelle période, et conditions si elles changent."""

    purchase_order_id: UUID
    start_date: date
    end_date: date
    days_sold: Decimal | None = None
    free_days: Decimal | None = None
    purchase_daily_rate: Decimal | None = None
    sale_daily_rate: Decimal | None = None
    created_by: UUID | None = None


class RenewPurchaseOrderUseCase:
    """Reconduit une mission par un nouveau bon de commande.

    Il n'y a pas de tacite reconduction : chaque prolongation donne lieu à un
    document distinct, numéroté à la suite et signé pour lui-même. Le nouveau
    bon de commande hérite du consultant, du fournisseur, du contrat cadre et
    de la mission ; seules la période et, le cas échéant, les conditions
    changent. Il pointe son parent par `parent_purchase_order_id`, ce qui
    permet de suivre une mission sur toute sa durée.
    """

    def __init__(
        self,
        purchase_order_repository,
        contract_request_repository,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._cr_repo = contract_request_repository

    async def execute(self, command: RenewPurchaseOrderCommand) -> PurchaseOrder:
        """Execute the use case.

        Returns:
            Le nouveau bon de commande, en brouillon.

        Raises:
            PurchaseOrderNotFoundError: If the source purchase order is unknown.
            InvalidPurchaseOrderDataError: If the source cannot be renewed or
                the new period is inconsistent.
        """
        source = await self._po_repo.get_by_id(command.purchase_order_id)
        if not source:
            raise PurchaseOrderNotFoundError(str(command.purchase_order_id))

        if source.status not in RENEWABLE_STATUSES:
            raise InvalidPurchaseOrderDataError(
                f"Le bon de commande {source.display_reference} n'est pas reconductible "
                f"(état : {source.status.display_name})."
            )
        if command.end_date < command.start_date:
            raise InvalidPurchaseOrderDataError(
                "La date de fin ne peut pas précéder la date de début."
            )

        days_sold = command.days_sold if command.days_sold is not None else source.days_sold
        free_days = command.free_days if command.free_days is not None else Decimal("0")
        if days_sold is not None and days_sold <= Decimal("0"):
            raise InvalidPurchaseOrderDataError(
                "Le nombre de jours vendus doit être supérieur à zéro."
            )
        if days_sold is not None and free_days > days_sold:
            raise InvalidPurchaseOrderDataError(
                "Les jours de gratuité ne peuvent pas dépasser les jours vendus."
            )

        # Comme toute création, la reconduction part d'un numéro provisoire :
        # elle prendra son rang dans la séquence à la génération du document.
        reference = await self._po_repo.get_next_provisional_reference()

        renewal = PurchaseOrder(
            provisional_reference=reference,
            parent_purchase_order_id=source.id,
            company_id=source.company_id,
            third_party_id=source.third_party_id,
            contract_request_id=source.contract_request_id,
            # Même mission, même consultant, même positionnement : la
            # reconduction ne crée pas un second positionnement dans Boond.
            boond_consultant_id=source.boond_consultant_id,
            boond_consultant_type=source.boond_consultant_type,
            consultant_civility=source.consultant_civility,
            consultant_first_name=source.consultant_first_name,
            consultant_last_name=source.consultant_last_name,
            consultant_email=source.consultant_email,
            consultant_phone=source.consultant_phone,
            boond_positioning_id=source.boond_positioning_id,
            boond_need_id=source.boond_need_id,
            boond_delivery_id=source.boond_delivery_id,
            client_name=source.client_name,
            mission_title=source.mission_title,
            mission_description=source.mission_description,
            mission_site_name=source.mission_site_name,
            mission_address=source.mission_address,
            mission_postal_code=source.mission_postal_code,
            mission_city=source.mission_city,
            purchase_daily_rate=(
                command.purchase_daily_rate
                if command.purchase_daily_rate is not None
                else source.purchase_daily_rate
            ),
            sale_daily_rate=(
                command.sale_daily_rate
                if command.sale_daily_rate is not None
                else source.sale_daily_rate
            ),
            days_sold=days_sold,
            free_days=free_days,
            start_date=command.start_date,
            end_date=command.end_date,
            commercial_email=source.commercial_email,
            created_by=command.created_by,
        )

        saved = await self._po_repo.save(renewal)
        logger.info(
            "purchase_order_renewed",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            parent_reference=source.display_reference,
            start_date=str(command.start_date),
            end_date=str(command.end_date),
        )
        return saved
