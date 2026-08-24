"""Use case: Undo what a purchase order pushed into BoondManager."""

from uuid import UUID

import structlog

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import PurchaseOrderNotFoundError

logger = structlog.get_logger()

# État où le positionnement se trouvait quand le bon de commande est né :
# 7, « Gagné attente contrat ». Le report l'a fait passer à « Gagné » pour
# créer la prestation ; défaire le report l'y ramène.
POSITIONING_STATE_BEFORE_PUSH = 7


class DeletePurchaseOrderFromBoondUseCase:
    """Supprime dans BoondManager ce que le report du bon de commande y a créé.

    **Outil de test.** Il sert à rejouer un report sur un dossier d'essai sans
    laisser derrière soi des achats et des contrats fantômes.

    L'ordre est celui de la création à l'envers — achat, contrat, prestation —,
    parce que l'achat pend à la prestation. Chaque objet est traité à part :
    l'échec de l'un n'empêche pas les autres. Un identifiant n'est effacé du
    bon de commande que si l'objet a bien disparu du CRM ; le garder est le
    seul moyen de ne pas créer un doublon au report suivant.

    Ce qui n'est **pas** défait : la conversion d'un candidat en ressource, que
    l'API ne sait pas annuler, et la société fournisseur, qui appartient au
    contrat cadre et sert à d'autres missions.
    """

    def __init__(self, purchase_order_repository, crm_service) -> None:
        self._po_repo = purchase_order_repository
        self._crm = crm_service

    async def execute(self, purchase_order_id: UUID) -> tuple[PurchaseOrder, list[str]]:
        """Execute the use case.

        Returns:
            Le bon de commande et le compte rendu, ligne à ligne.

        Raises:
            PurchaseOrderNotFoundError: If the purchase order does not exist.
        """
        po = await self._po_repo.get_by_id(purchase_order_id)
        if not po:
            raise PurchaseOrderNotFoundError(str(purchase_order_id))

        report: list[str] = []
        supprimes = 0

        for champ, libelle, methode in (
            ("boond_purchase_order_id", "Achat", self._crm.delete_supplier_purchase),
            ("boond_contract_id", "Contrat", self._crm.delete_boond_contract),
            ("boond_delivery_id", "Prestation", self._crm.delete_delivery),
        ):
            identifiant = getattr(po, champ)
            if not identifiant:
                continue
            try:
                await methode(identifiant)
            except Exception as exc:
                logger.warning(
                    "purchase_order_boond_delete_failed",
                    purchase_order_id=str(po.id),
                    kind=champ,
                    boond_id=identifiant,
                    error=_readable_error(exc),
                )
                report.append(f"{libelle} #{identifiant} : suppression refusée par Boond.")
                continue
            setattr(po, champ, None)
            supprimes += 1
            report.append(f"{libelle} #{identifiant} supprimé.")

        if not report:
            report.append("Rien n'avait été poussé dans BoondManager.")

        # Le positionnement est repassé à « Gagné » par le report : c'est ce
        # qui a fait naître la prestation. Le laisser là ferait croire la
        # mission gagnée alors qu'on vient d'en effacer les traces.
        if supprimes and po.boond_positioning_id:
            try:
                await self._crm.update_positioning_state(
                    po.boond_positioning_id, POSITIONING_STATE_BEFORE_PUSH
                )
                report.append(
                    f"Positionnement {po.boond_positioning_id} ramené à « Gagné attente contrat »."
                )
            except Exception as exc:
                logger.warning(
                    "purchase_order_positioning_reset_failed",
                    purchase_order_id=str(po.id),
                    positioning_id=po.boond_positioning_id,
                    error=_readable_error(exc),
                )
                report.append(
                    f"Positionnement {po.boond_positioning_id} laissé à « Gagné » : "
                    "à remettre à la main dans BoondManager."
                )

        if po.boond_consultant_type == "resource":
            report.append(
                "La ressource reste : BoondManager ne sait pas la reconvertir en candidat."
            )

        po.boond_sync_error = None
        saved = await self._po_repo.save(po)
        logger.info(
            "purchase_order_boond_push_undone",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            deleted=supprimes,
        )
        return saved, report


def _readable_error(exc: Exception) -> str:
    """Extrait un message exploitable d'une erreur HTTP Boond."""
    cause = exc.__cause__ or getattr(exc, "__context__", None)
    response = getattr(cause, "response", None) or getattr(exc, "response", None)
    if response is not None:
        return f"Boond HTTP {response.status_code}: {response.text[:500]}"
    return str(exc)
