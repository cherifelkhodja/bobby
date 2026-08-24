"""Use case: Attach a BoondManager delivery to a purchase order by hand."""

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


class AttachDeliveryToPurchaseOrderUseCase:
    """Rattache à la main la prestation Boond d'une mission.

    Le report la trouve normalement seul, en passant le positionnement à
    « Gagné » puis en le relisant. Quand cette lecture ne la rend pas — alors
    que le CRM l'a bien créée —, la mission reste bloquée : l'achat fournisseur
    se rattache à la prestation, et rien ne permettait de dire à Bobby laquelle.

    Ce rattachement ne passe pas par la modification ordinaire d'un bon de
    commande, qui s'arrête au brouillon : le report a lieu **après** la
    signature, soit précisément là où la mission n'est plus modifiable. Il
    n'écrit rien dans le document non plus — la prestation est un lien de CRM,
    elle ne s'imprime pas —, donc rien à régénérer.
    """

    def __init__(self, purchase_order_repository, crm_service) -> None:
        self._po_repo = purchase_order_repository
        self._crm = crm_service

    async def execute(self, purchase_order_id: UUID, delivery_id: int) -> PurchaseOrder:
        """Execute the use case.

        Returns:
            Le bon de commande, sa prestation rattachée.

        Raises:
            PurchaseOrderNotFoundError: If the purchase order does not exist.
            InvalidPurchaseOrderDataError: If the order is cancelled, or if
                BoondManager ne rend pas cette prestation.
        """
        po = await self._po_repo.get_by_id(purchase_order_id)
        if not po:
            raise PurchaseOrderNotFoundError(str(purchase_order_id))

        if po.status == PurchaseOrderStatus.CANCELLED:
            raise InvalidPurchaseOrderDataError(
                "Le bon de commande est annulé : sa prestation ne se rattache plus."
            )

        # La prestation est relue avant d'être retenue. Un numéro saisi de
        # travers poserait l'achat sur la mission d'un autre consultant, et un
        # achat mal rattaché ne se corrige pas : `PUT /purchases/{id}` n'expose
        # pas `delivery`, il faut le supprimer et le recréer.
        delivery = await self._crm.get_delivery(delivery_id)
        if not delivery:
            raise InvalidPurchaseOrderDataError(
                f"BoondManager ne rend aucune prestation {delivery_id} : vérifiez le numéro, "
                "ou réessayez si le CRM est momentanément injoignable."
            )

        po.boond_delivery_id = delivery_id
        # L'avertissement du report portait sur la prestation manquante : le
        # laisser afficherait un blocage levé.
        po.boond_sync_error = None

        saved = await self._po_repo.save(po)
        logger.info(
            "purchase_order_delivery_attached",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            delivery_id=delivery_id,
            delivery_title=delivery.get("title"),
            delivery_resource_id=delivery.get("resource_id"),
        )
        return saved
