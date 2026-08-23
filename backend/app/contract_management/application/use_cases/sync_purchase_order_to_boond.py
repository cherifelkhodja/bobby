"""Use case: Push a signed purchase order to BoondManager."""

from datetime import date
from uuid import UUID

import structlog

from app.contract_management.application.boond_mappings import (
    contract_type_of,
    resource_type_of,
    state_reason_type_of,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    PurchaseOrderBoondSyncError,
    PurchaseOrderNotFoundError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

logger = structlog.get_logger()

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

        warnings: list[str] = []
        try:
            resource_id = await self._resolve_resource(po)
            await self._link_provider(po, resource_id, third_party.boond_provider_id)
            await self._create_contract(po, resource_id)
            await self._create_purchase_order(po, third_party.boond_provider_id, warnings)
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

        # Le report a abouti, mais quelque chose reste à reprendre à la main :
        # le message est porté par le même champ que les erreurs, seul canal
        # visible de l'ADV sur le dossier.
        if warnings:
            po.boond_sync_error = " ".join(warnings)

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

        # Le type de tiers du fournisseur classe la ressource dans Boond :
        # externe pour la sous-traitance et le portage salarial, type dédié pour
        # le portage commercial. Sans lui, la ressource naîtrait mal classée.
        third_party_type = await self._third_party_type(po)
        resource_id = await self._crm.convert_candidate_to_resource(
            po.boond_consultant_id,
            state=RESOURCE_STATE_ARRIVING,
            state_reason_type_of=state_reason_type_of(third_party_type),
            type_of=resource_type_of(third_party_type),
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

    async def _create_purchase_order(
        self, po: PurchaseOrder, provider_id: int, warnings: list[str]
    ) -> None:
        """Crée le bon de commande Boond, au montant d'achat de la mission.

        Une reconduction passe d'abord par le renouvellement natif de la
        prestation, qui produit lui-même l'achat fournisseur et la commande
        client. On ne crée un bon de commande que si ce renouvellement n'en a
        pas produit — ou s'il n'y a pas de prestation à renouveler.
        """
        if po.boond_purchase_order_id:
            return

        if po.parent_purchase_order_id and po.boond_delivery_id:
            await self._renew_delivery(po, warnings)
            if po.boond_purchase_order_id:
                return

        boond_po_id = await self._crm.create_purchase_order(
            provider_id=provider_id,
            positioning_id=po.boond_positioning_id,
            reference=po.reference,
            amount=float(po.total_amount),
        )
        po.boond_purchase_order_id = boond_po_id

    async def _renew_delivery(self, po: PurchaseOrder, warnings: list[str]) -> None:
        """Renouvelle la prestation Boond et la recale sur la nouvelle période.

        Boond duplique la prestation à l'identique : sans recalage, la nouvelle
        porterait les dates de la précédente.
        """
        renewed = await self._crm.renew_delivery(po.boond_delivery_id)
        if not renewed or not renewed.get("id"):
            raise PurchaseOrderBoondSyncError(
                po.reference, "le renouvellement de la prestation n'a rien retourné"
            )

        source_delivery_id = po.boond_delivery_id
        po.boond_delivery_id = renewed["id"]
        if renewed.get("purchase_id"):
            po.boond_purchase_order_id = renewed["purchase_id"]
        if renewed.get("contract_id"):
            po.boond_contract_id = renewed["contract_id"]

        try:
            await self._crm.update_delivery(
                delivery_id=po.boond_delivery_id,
                start_date=_iso(po.start_date),
                end_date=_iso(po.end_date),
                days_sold=float(po.days_sold) if po.days_sold is not None else None,
                free_days=float(po.free_days or 0),
                purchase_daily_rate=(
                    float(po.purchase_daily_rate) if po.purchase_daily_rate is not None else None
                ),
                sale_daily_rate=(
                    float(po.sale_daily_rate) if po.sale_daily_rate is not None else None
                ),
            )
        except Exception as exc:
            # La prestation existe et l'achat est créé : l'échec du recalage ne
            # doit pas invalider la synchronisation, mais l'ADV doit le savoir.
            logger.warning(
                "purchase_order_delivery_alignment_failed",
                purchase_order_id=str(po.id),
                delivery_id=po.boond_delivery_id,
                error=_readable_error(exc),
            )
            warnings.append(
                f"Prestation {po.boond_delivery_id} renouvelée depuis {source_delivery_id}, "
                "mais ses dates et quantités n'ont pas pu être mises à jour : "
                "à recaler dans BoondManager."
            )

    async def _third_party_type(self, po: PurchaseOrder) -> str:
        """Type de tiers du fournisseur : celui du cadre, sinon celui de la fiche."""
        if po.contract_request_id:
            framework = await self._cr_repo.get_by_id(po.contract_request_id)
            if framework and framework.third_party_type:
                return framework.third_party_type
        if po.third_party_id:
            third_party = await self._tp_repo.get_by_id(po.third_party_id)
            if third_party:
                return third_party.type.value
        return ""

    async def _contract_type_of(self, po: PurchaseOrder) -> int:
        """Type de contrat Boond, déduit du type de tiers du fournisseur."""
        return contract_type_of(await self._third_party_type(po))

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
