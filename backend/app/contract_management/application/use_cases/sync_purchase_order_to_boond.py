"""Use case: Push a signed purchase order to BoondManager."""

from datetime import date
from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    PurchaseOrderBoondSyncError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

logger = structlog.get_logger()

# third_party_type → typeOf du contrat Boond. Repris de la synchronisation du
# contrat cadre pour que les deux chemins classent les contrats à l'identique.
THIRD_PARTY_TYPE_TO_CONTRACT_TYPE: dict[str, int] = {
    "sous_traitant": 2,
    "freelance": 3,
    "portage_salarial": 6,
    "portage_commercial": 7,
}

# État Boond « Arrivée prochaine » d'une ressource fraîchement convertie.
RESOURCE_STATE_ARRIVING = 3


class SyncPurchaseOrderToBoondUseCase:
    """Reporte un bon de commande signé dans BoondManager.

    Trois écritures, chacune idempotente : la ressource (conversion du candidat
    puis rattachement au fournisseur), le contrat Boond qui porte le CJM et les
    dates, et le bon de commande qui porte le montant d'achat. Une erreur est
    conservée sur le bon de commande pour que l'ADV puisse relancer sans
    reprendre les étapes déjà passées.
    """

    def __init__(
        self,
        purchase_order_repository,
        contract_request_repository,
        third_party_repository,
        crm_service,
        db=None,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service
        self._db = db

    async def execute(self, purchase_order_id: UUID) -> PurchaseOrder:
        """Execute the use case.

        Returns:
            The purchase order, ACTIVE once BoondManager is up to date.

        Raises:
            PurchaseOrderNotFoundError: If the purchase order does not exist.
            PurchaseOrderBoondSyncError: If a prerequisite is missing or a
                BoondManager call fails.
        """
        po = await self._po_repo.get_by_id(purchase_order_id)
        if not po:
            raise PurchaseOrderNotFoundError(str(purchase_order_id))

        if po.status not in (PurchaseOrderStatus.SIGNED, PurchaseOrderStatus.ACTIVE):
            raise PurchaseOrderBoondSyncError(
                po.reference,
                f"le bon de commande doit être signé (état actuel : {po.status.display_name})",
            )

        third_party = (
            await self._tp_repo.get_by_id(po.third_party_id) if po.third_party_id else None
        )
        if not third_party or not third_party.boond_provider_id:
            raise PurchaseOrderBoondSyncError(
                po.reference,
                "la société fournisseur n'existe pas encore dans BoondManager "
                "(elle est créée à la signature du contrat cadre)",
            )
        if not po.boond_positioning_id:
            raise PurchaseOrderBoondSyncError(
                po.reference, "aucun positionnement Boond n'est rattaché"
            )

        try:
            resource_id = await self._resolve_resource(po)
            await self._link_provider(po, resource_id, third_party.boond_provider_id)
            await self._create_contract(po, resource_id)
            await self._create_purchase_order(po, third_party.boond_provider_id)
        except PurchaseOrderBoondSyncError:
            raise
        except Exception as exc:
            po.boond_sync_error = _readable_error(exc)
            await self._po_repo.save(po)
            logger.error(
                "purchase_order_boond_sync_failed",
                purchase_order_id=str(po.id),
                reference=po.reference,
                error=po.boond_sync_error,
            )
            raise PurchaseOrderBoondSyncError(po.reference, po.boond_sync_error)

        if po.status == PurchaseOrderStatus.SIGNED:
            po.mark_active()
        else:
            po.boond_sync_error = None

        saved = await self._po_repo.save(po)
        logger.info(
            "purchase_order_boond_sync_completed",
            purchase_order_id=str(saved.id),
            reference=saved.reference,
            boond_contract_id=saved.boond_contract_id,
            boond_purchase_order_id=saved.boond_purchase_order_id,
        )
        return saved

    async def _resolve_resource(self, po: PurchaseOrder) -> int:
        """Retourne l'ID ressource Boond du consultant, en le convertissant au besoin.

        Un consultant encore candidat devient ressource à la signature du bon de
        commande : c'est ce document qui acte sa mission.
        """
        if not po.boond_consultant_id:
            raise PurchaseOrderBoondSyncError(po.reference, "aucun consultant Boond rattaché")

        if po.boond_consultant_type == "resource":
            return po.boond_consultant_id

        existing = await self._crm.resolve_resource_id(po.boond_consultant_id)
        if existing:
            return existing

        resource_id = await self._crm.convert_candidate_to_resource(
            po.boond_consultant_id, state=RESOURCE_STATE_ARRIVING
        )
        if not resource_id:
            raise PurchaseOrderBoondSyncError(
                po.reference, "la conversion du candidat en ressource a échoué"
            )
        logger.info(
            "purchase_order_candidate_converted",
            purchase_order_id=str(po.id),
            candidate_id=po.boond_consultant_id,
            resource_id=resource_id,
        )
        return resource_id

    async def _link_provider(self, po: PurchaseOrder, resource_id: int, provider_id: int) -> None:
        """Rattache la ressource à sa société fournisseur (best-effort).

        Un échec ici ne doit pas empêcher la création du contrat et du bon de
        commande : le lien est corrigeable à la main dans Boond.
        """
        try:
            await self._crm.update_resource_administrative(
                resource_id=resource_id,
                provider_company_id=provider_id,
                provider_contact_id=None,
            )
        except Exception as exc:
            logger.warning(
                "purchase_order_provider_link_failed",
                purchase_order_id=str(po.id),
                resource_id=resource_id,
                error=str(exc),
            )

    async def _create_contract(self, po: PurchaseOrder, resource_id: int) -> None:
        """Crée le contrat Boond portant le CJM et les dates de la mission.

        Rien n'est créé pour une reconduction : le consultant reste sous le même
        contrat de sous-traitance, seule son échéance recule. En créer un second
        superposerait deux contrats actifs sur la même ressource et fausserait
        les coûts calculés par Boond.

        # NEEDS-CONFIRMATION : le renouvellement natif de la prestation
        # (POST /deliveries/{id}/renew, qui crée l'achat et la commande client)
        # est la voie visée pour reculer cette échéance ; le corps de requête
        # attendu reste à confirmer avant de le brancher.
        """
        if po.boond_contract_id:
            return

        if po.parent_purchase_order_id:
            logger.info(
                "purchase_order_renewal_keeps_existing_contract",
                purchase_order_id=str(po.id),
                reference=po.reference,
                delivery_id=po.boond_delivery_id,
            )
            return

        contract_id = await self._crm.create_boond_contract(
            resource_id=resource_id,
            positioning_id=po.boond_positioning_id,
            daily_rate=float(po.purchase_daily_rate or 0),
            type_of=await self._contract_type_of(po),
            start_date=_iso(po.start_date),
            end_date=_iso(po.end_date),
            agency_id=await self._agency_id(po),
        )
        po.boond_contract_id = contract_id

    async def _create_purchase_order(self, po: PurchaseOrder, provider_id: int) -> None:
        """Crée le bon de commande Boond, au montant d'achat de la mission."""
        if po.boond_purchase_order_id:
            return

        boond_po_id = await self._crm.create_purchase_order(
            provider_id=provider_id,
            positioning_id=po.boond_positioning_id,
            reference=po.reference,
            amount=float(po.total_amount),
        )
        po.boond_purchase_order_id = boond_po_id

    async def _contract_type_of(self, po: PurchaseOrder) -> int:
        """Type de contrat Boond, déduit du type de tiers du fournisseur."""
        third_party_type = ""
        if po.contract_request_id:
            framework = await self._cr_repo.get_by_id(po.contract_request_id)
            third_party_type = (framework.third_party_type if framework else "") or ""
        if not third_party_type and po.third_party_id:
            third_party = await self._tp_repo.get_by_id(po.third_party_id)
            third_party_type = third_party.type.value if third_party else ""
        return THIRD_PARTY_TYPE_TO_CONTRACT_TYPE.get(third_party_type, 3)

    async def _agency_id(self, po: PurchaseOrder) -> int | None:
        """Agence Boond de la société émettrice du bon de commande."""
        if self._db is None or not po.company_id:
            return None
        from sqlalchemy import select

        from app.contract_management.infrastructure.models import ContractCompanyModel

        result = await self._db.execute(
            select(ContractCompanyModel.boond_agency_id).where(
                ContractCompanyModel.id == po.company_id
            )
        )
        return result.scalar_one_or_none()


def _iso(value: date | None) -> str | None:
    """Date au format attendu par l'API Boond (YYYY-MM-DD)."""
    return value.isoformat() if isinstance(value, date) else None


def _readable_error(exc: Exception) -> str:
    """Extrait un message exploitable d'une erreur HTTP Boond.

    Les appels passent par `tenacity` : l'erreur utile est portée par la
    dernière tentative, ou par la cause de l'exception relayée.
    """
    cause = exc.__cause__ or getattr(exc, "__context__", None)
    response = getattr(cause, "response", None)
    if response is not None:
        return f"Boond HTTP {response.status_code}: {response.text[:500]}"

    last_attempt = getattr(exc, "last_attempt", None)
    if last_attempt is not None:
        inner = last_attempt.exception()
        inner_response = getattr(inner, "response", None)
        if inner_response is not None:
            return f"Boond HTTP {inner_response.status_code}: {inner_response.text[:500]}"
        if inner:
            return str(inner)
    return str(exc)
