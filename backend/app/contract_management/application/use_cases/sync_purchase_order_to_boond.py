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

# Clé de configuration runtime (table `app_settings`) : état « Gagné » d'un
# positionnement. C'est lui qui fait naître la prestation — Boond la crée à
# partir du positionnement au passage à cet état, l'API n'offrant aucun moyen
# de la créer directement.
WON_STATE_SETTING_KEY = "bdc_won_positioning_state"

# Libellé de l'état recherché dans le dictionnaire du CRM. Chaque entité Boond
# a sa propre échelle : l'état 1 d'une opportunité est « Gagné », celui d'un
# positionnement « Refus Client ». Les confondre écrit un refus sur une affaire
# gagnée — c'est arrivé.
WON_STATE_LABEL = "gagne"

# Valeur configurée dans le CRM aujourd'hui, dernier recours si le dictionnaire
# est illisible. Un dictionnaire lisible qui ne connaît pas « Gagné » ne mène
# pas ici : le libellé a changé, et deviner serait reprendre le risque.
DEFAULT_WON_STATE = 2

# « Gagné attente contrat » commence pareil sans désigner le même état : la
# correspondance est exacte, jamais par préfixe.
_ACCENTS = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")

# Ce que BoondManager exige pour porter la mission : le contrat vit du CJM et
# des dates, l'achat du montant qui en découle. Le reste du bon de commande —
# client final, société émettrice, intitulé — ne monte pas dans le CRM et ne
# doit donc pas retenir le report.
REQUIRED_FOR_BOOND: tuple[tuple[str, str], ...] = (
    ("purchase_daily_rate", "le CJM (coût journalier d'achat)"),
    ("days_sold", "le nombre de jours vendus"),
    ("start_date", "la date de début"),
    ("end_date", "la date de fin"),
)


class SyncPurchaseOrderToBoondUseCase:
    """Reporte un bon de commande dans BoondManager.

    Quatre écritures, chacune idempotente : la ressource (conversion du
    candidat puis rattachement au fournisseur), le contrat Boond qui porte le
    CJM et les dates, la prestation que fait naître le positionnement gagné, et
    l'achat fournisseur qui pend à cette prestation. Ce qui a abouti est
    conservé sur le bon de commande, pour qu'une relance reprenne là où le
    report s'est arrêté au lieu de tout rejouer.
    """

    def __init__(
        self,
        purchase_order_repository,
        contract_request_repository,
        third_party_repository,
        crm_service,
        db=None,
        settings_service=None,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service
        self._db = db
        self._settings = settings_service

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

        # Le report n'attend pas la signature : l'ADV a souvent besoin de la
        # ressource et de la prestation dans le CRM pendant que le bon de
        # commande circule. Il exige en revanche une mission complète — c'est
        # elle qui alimente le contrat et l'achat Boond.
        if po.status == PurchaseOrderStatus.CANCELLED:
            raise PurchaseOrderBoondSyncError(po.display_reference, "le bon de commande est annulé")
        missing = [label for attr, label in REQUIRED_FOR_BOOND if getattr(po, attr) is None]
        if missing:
            raise PurchaseOrderBoondSyncError(
                po.display_reference,
                "les conditions de la mission sont incomplètes : il manque " + ", ".join(missing),
            )

        third_party = (
            await self._tp_repo.get_by_id(po.third_party_id) if po.third_party_id else None
        )
        if not third_party or not third_party.boond_provider_id:
            raise PurchaseOrderBoondSyncError(
                po.display_reference,
                "la société fournisseur n'existe pas encore dans BoondManager "
                "(elle est créée à la signature du contrat cadre)",
            )
        if not po.boond_positioning_id:
            raise PurchaseOrderBoondSyncError(
                po.display_reference, "aucun positionnement Boond n'est rattaché"
            )

        warnings: list[str] = []
        try:
            resource_id = await self._resolve_resource(po)
            await self._link_provider(po, resource_id, third_party)
            await self._create_contract(po, resource_id)
            await self._ensure_delivery(po, warnings)
            await self._create_purchase_order(po, third_party, warnings)
        except PurchaseOrderBoondSyncError:
            raise
        except Exception as exc:
            po.boond_sync_error = _readable_error(exc)
            await self._po_repo.save(po)
            logger.error(
                "purchase_order_boond_sync_failed",
                purchase_order_id=str(po.id),
                reference=po.display_reference,
                error=po.boond_sync_error,
            )
            raise PurchaseOrderBoondSyncError(po.display_reference, po.boond_sync_error)

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
            reference=saved.display_reference,
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
            raise PurchaseOrderBoondSyncError(
                po.display_reference, "aucun consultant Boond rattaché"
            )

        if po.boond_consultant_type == "resource":
            return po.boond_consultant_id

        existing = await self._crm.resolve_resource_id(po.boond_consultant_id)
        if existing:
            self._remember_resource(po, existing)
            return existing

        # Le consultant peut déjà être une ressource : identifiant saisi tel
        # quel, ou positionnement dont Boond n'a pas dit la nature. Le convertir
        # échouerait — `PUT /candidates/{id}` sur un numéro qui n'est pas celui
        # d'un candidat. La sonde n'a lieu que si aucun candidat ne porte ce
        # numéro : candidats et ressources ont deux séries d'identifiants, et le
        # même numéro peut désigner deux personnes.
        if not await self._crm.candidate_exists(po.boond_consultant_id):
            if await self._crm.resource_exists(po.boond_consultant_id):
                logger.info(
                    "purchase_order_consultant_already_a_resource",
                    purchase_order_id=str(po.id),
                    resource_id=po.boond_consultant_id,
                )
                self._remember_resource(po, po.boond_consultant_id)
                return po.boond_consultant_id
            raise PurchaseOrderBoondSyncError(
                po.display_reference,
                f"le consultant {po.boond_consultant_id} est introuvable dans BoondManager, "
                "ni comme candidat ni comme ressource",
            )

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
                po.display_reference, "la conversion du candidat en ressource a échoué"
            )
        logger.info(
            "purchase_order_candidate_converted",
            purchase_order_id=str(po.id),
            candidate_id=po.boond_consultant_id,
            resource_id=resource_id,
        )
        self._remember_resource(po, resource_id)
        return resource_id

    @staticmethod
    def _remember_resource(po: PurchaseOrder, resource_id: int) -> None:
        """Retient la ressource : un second report ne repasse pas par Boond.

        C'est aussi ce qui fait apparaître « ressource » à l'écran, là où le
        consultant s'affichait encore comme candidat après sa conversion.
        """
        po.boond_consultant_id = resource_id
        po.boond_consultant_type = "resource"

    async def _link_provider(self, po: PurchaseOrder, resource_id: int, third_party) -> None:
        """Rattache la ressource à sa société fournisseur et à son contact.

        Boond attend un contact autant qu'une société : c'est l'interlocuteur
        du fournisseur pour ce consultant. Celui de la facturation est retenu,
        comme au report du contrat cadre ; à défaut, l'ADV, puis le signataire —
        mieux vaut un contact approchant que pas de contact du tout.

        Best-effort : un échec ici ne doit pas empêcher la création du contrat
        et de l'achat, le lien restant corrigeable à la main dans Boond.
        """
        try:
            await self._crm.update_resource_administrative(
                resource_id=resource_id,
                provider_company_id=third_party.boond_provider_id,
                provider_contact_id=_provider_contact_id(third_party),
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
                reference=po.display_reference,
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
        self, po: PurchaseOrder, third_party, warnings: list[str]
    ) -> None:
        """Crée l'achat fournisseur Boond sur la prestation de la mission.

        L'achat pend à la prestation : sans elle, il n'a rien à quoi se
        rattacher, et ce rattachement ne se fait qu'à la création. Rien n'est
        créé si le renouvellement natif d'une reconduction en a déjà produit un.

        Le montant ne lui est pas dicté : Boond le pré-remplit depuis la
        prestation, que `_align_delivery` vient d'accorder au CJM et aux jours
        du bon de commande. C'est un montant **unitaire** que Boond multiplie
        ensuite par la quantité — lui poser le total du bon de commande le
        faisait multiplier une seconde fois.
        """
        # Une reconduction reçoit son achat du renouvellement natif de la
        # prestation, qui le produit lui-même avec la commande client.
        if po.boond_purchase_order_id:
            return

        if not po.boond_delivery_id:
            warnings.append(
                "L'achat fournisseur n'a pas été créé : il se rattache à la prestation, "
                "qui manque encore. Reprenez le report une fois la prestation en place."
            )
            return

        try:
            po.boond_purchase_order_id = await self._crm.create_supplier_purchase(
                delivery_id=po.boond_delivery_id,
                title=_purchase_title(po),
                provider_id=third_party.boond_provider_id,
                provider_contact_id=_provider_contact_id(third_party),
                reference=po.display_reference,
                start_date=_iso(po.start_date),
                end_date=_iso(po.end_date),
                vat_liable=getattr(third_party, "vat_liable", True),
            )
        except Exception as exc:
            # La ressource, le contrat et la prestation sont en place : les
            # rejouer pour un achat manqué ferait plus de dégâts que de bien.
            # L'ADV le saisit dans Boond, ou relance le report.
            logger.warning(
                "purchase_order_supplier_purchase_failed",
                purchase_order_id=str(po.id),
                delivery_id=po.boond_delivery_id,
                error=_readable_error(exc),
            )
            warnings.append(
                f"Achat fournisseur non créé sur la prestation {po.boond_delivery_id} : "
                "à saisir dans BoondManager."
            )

    async def _ensure_delivery(self, po: PurchaseOrder, warnings: list[str]) -> None:
        """Fait exister la prestation Boond, puis la met d'accord avec le bon de commande.

        Bobby ne crée pas de prestation — l'API ne le permet pas. Il fait
        passer le positionnement à « Gagné », et Boond la produit à partir de
        lui. Une reconduction, elle, part de la prestation en cours et la
        renouvelle : c'est ce renouvellement qui la recale et produit l'achat.
        Une reconduction sans prestation connue — mission dont le premier bon
        de commande n'a jamais été reporté — n'a rien à renouveler et repasse
        donc par le positionnement.

        Le positionnement est gagné **même si une prestation existe déjà** :
        c'est l'état de la mission, pas seulement le moyen d'en produire une.
        Un positionnement en porte une dès « Gagné attente contrat », l'état
        où s'ouvre le bon de commande — s'en remettre à son absence laissait
        la mission en attente dans le CRM une fois le report passé.
        """
        if po.parent_purchase_order_id and po.boond_delivery_id:
            await self._renew_delivery(po, warnings)
            return

        await self._win_positioning(po, warnings)

        if po.boond_delivery_id:
            await self._align_delivery(po, warnings)

    async def _win_positioning(self, po: PurchaseOrder, warnings: list[str]) -> None:
        """Passe le positionnement à « Gagné » et retient la prestation qui en naît.

        Seul l'état change : les données du positionnement — dates, tarif de
        vente, jours — restent celles du commercial. Les conditions du bon de
        commande sont portées à la prestation ensuite (`_align_delivery`), pas
        au positionnement.

        L'état est relu ensuite : BoondManager peut accepter la demande sans
        l'appliquer, et un report qui n'aurait rien changé doit se voir.
        """
        won = await self._won_state(warnings)
        if won is None:
            return

        try:
            echoed = await self._crm.update_positioning_state(po.boond_positioning_id, won)
        except Exception as exc:
            # Le contrat et l'achat restent créables : l'ADV reprendra la
            # prestation à la main plutôt que de tout rejouer.
            motif = _readable_error(exc)
            logger.warning(
                "purchase_order_positioning_win_failed",
                purchase_order_id=str(po.id),
                positioning_id=po.boond_positioning_id,
                error=motif,
            )
            # Le motif rendu par Boond est la seule information exploitable :
            # sans lui, l'ADV ne sait pas s'il doit corriger le dossier,
            # demander un droit, ou appeler l'éditeur.
            warnings.append(
                f"Positionnement {po.boond_positioning_id} non passé à « Gagné » "
                f"({motif}) : la prestation n'a pas été créée, à reprendre dans BoondManager."
            )
            return

        positioning = await self._crm.get_positioning(po.boond_positioning_id) or {}

        state = positioning.get("state")
        if state is not None and int(state) != won:
            # Deux pannes différentes, que seul l'écho de l'écriture sépare :
            # une demande ignorée d'emblée, ou un changement pris puis défait
            # par une règle du CRM. La distinction oriente la reprise.
            ignoree = isinstance(echoed, int) and echoed != won
            logger.warning(
                "purchase_order_positioning_state_unchanged",
                purchase_order_id=str(po.id),
                positioning_id=po.boond_positioning_id,
                state=state,
                echoed_state=echoed if isinstance(echoed, int) else None,
                ignored_outright=ignoree,
            )
            warnings.append(
                f"Positionnement {po.boond_positioning_id} : BoondManager a accepté la "
                f"demande mais l'état est resté à {state} — "
                + (
                    "le changement n'a même pas été pris en compte dans sa réponse. "
                    if ignoree
                    else ""
                )
                + "À passer à « Gagné » à la main."
            )

        if po.boond_delivery_id:
            return

        # Un positionnement n'expose pas de relation `delivery` : la prestation
        # se retrouve par le projet, que Boond remplit au passage à « Gagné ».
        # La lecture directe reste tentée d'abord, au cas où le CRM la rendrait.
        delivery_id = positioning.get("delivery_id") or await self._find_delivery(po, positioning)
        if delivery_id:
            po.boond_delivery_id = delivery_id
            logger.info(
                "purchase_order_delivery_created",
                purchase_order_id=str(po.id),
                positioning_id=po.boond_positioning_id,
                delivery_id=delivery_id,
            )
            return

        warnings.append(
            f"Positionnement {po.boond_positioning_id} passé à « Gagné », mais la prestation "
            "n'a pas été retrouvée : relevez son numéro dans BoondManager et rattachez-la "
            "sur le bon de commande, puis relancez le report."
        )

    async def _find_delivery(self, po: PurchaseOrder, positioning: dict) -> int | None:
        """Cherche la prestation par le projet du positionnement.

        Best-effort : ce qu'elle ne trouve pas se rattrape par la saisie de
        l'ADV, et une lecture qui échoue ne doit pas retenir le contrat.
        """
        project_id = positioning.get("project_id")
        if not project_id:
            return None
        try:
            return await self._crm.find_project_delivery(
                project_id,
                # La prestation dépend de la ressource, pas du candidat : le
                # consultant est déjà converti à ce stade du report.
                resource_id=po.boond_consultant_id
                if po.boond_consultant_type == "resource"
                else None,
            )
        except Exception as exc:
            logger.warning(
                "purchase_order_delivery_lookup_failed",
                purchase_order_id=str(po.id),
                project_id=project_id,
                error=_readable_error(exc),
            )
            return None

    async def _won_state(self, warnings: list[str]) -> int | None:
        """Valeur de l'état « Gagné » pour un positionnement, dans ce CRM.

        Elle est **lue**, jamais supposée : chaque entité Boond a sa propre
        échelle d'états, et se tromper d'échelle écrit un refus sur une affaire
        gagnée. L'ordre est celui de la confiance — ce que l'administrateur a
        réglé, puis ce que le dictionnaire du CRM déclare. À défaut des deux, le
        positionnement n'est pas touché : mieux vaut une prestation à créer à la
        main qu'un état faux.
        """
        configure = await self._configured_won_state()
        if configure is not None:
            return configure

        states = await self._crm.positioning_states()
        if not states:
            # Dictionnaire injoignable : la valeur du CRM reste la meilleure
            # connue, et s'abstenir priverait le report de sa prestation.
            logger.warning("purchase_order_won_state_from_default", state=DEFAULT_WON_STATE)
            return DEFAULT_WON_STATE

        exacts = [value for value, label in states.items() if _normalise(label) == WON_STATE_LABEL]
        if len(exacts) == 1:
            return exacts[0]

        # Le dictionnaire répond mais ne connaît pas « Gagné » : le libellé a
        # été changé. Écrire un numéro au jugé remettrait un refus sur une
        # affaire gagnée.
        logger.warning("purchase_order_won_state_unresolved", states=states, matches=exacts)
        warnings.append(
            "L'état « Gagné » d'un positionnement n'a pas pu être déterminé dans "
            "BoondManager : la prestation n'a pas été créée. Renseignez le réglage "
            f"« {WON_STATE_SETTING_KEY} » avec sa valeur numérique."
        )
        return None

    async def _configured_won_state(self) -> int | None:
        """Valeur réglée par l'administrateur, si elle l'a été."""
        if not self._settings:
            return None
        raw = await self._settings.get(WON_STATE_SETTING_KEY)
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            logger.warning("bdc_won_state_invalid", value=raw)
            return None

    async def _align_delivery(self, po: PurchaseOrder, warnings: list[str]) -> None:
        """Recale la prestation Boond sur les conditions du bon de commande.

        Période, jours vendus, gratuité et CJM d'achat viennent du document que
        le fournisseur signe. Le **prix de vente au client n'est pas touché** :
        il relève du commercial, pas d'un document d'achat.
        """
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
            )
            logger.info(
                "purchase_order_delivery_aligned",
                purchase_order_id=str(po.id),
                delivery_id=po.boond_delivery_id,
            )
        except Exception as exc:
            # Le contrat et l'achat restent créables : l'ADV recalera la
            # prestation à la main plutôt que de tout rejouer.
            logger.warning(
                "purchase_order_delivery_alignment_failed",
                purchase_order_id=str(po.id),
                delivery_id=po.boond_delivery_id,
                error=_readable_error(exc),
            )
            warnings.append(
                f"Prestation {po.boond_delivery_id} non recalée sur la période et les "
                "conditions du bon de commande : à reprendre dans BoondManager."
            )

    async def _renew_delivery(self, po: PurchaseOrder, warnings: list[str]) -> None:
        """Renouvelle la prestation Boond et la recale sur la nouvelle période.

        Boond duplique la prestation à l'identique : sans recalage, la nouvelle
        porterait les dates de la précédente.
        """
        renewed = await self._crm.renew_delivery(po.boond_delivery_id)
        if not renewed or not renewed.get("id"):
            raise PurchaseOrderBoondSyncError(
                po.display_reference, "le renouvellement de la prestation n'a rien retourné"
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


def _provider_contact_id(third_party) -> int | None:
    """Contact du fournisseur à rattacher à la ressource : facturation, ADV, signataire."""
    for field in ("boond_billing_contact_id", "boond_adv_contact_id", "boond_signatory_contact_id"):
        contact_id = getattr(third_party, field, None)
        if contact_id:
            return contact_id
    return None


def _normalise(label: str) -> str:
    """Libellé comparable : sans accents, sans casse, sans espaces de bord."""
    return (label or "").strip().lower().translate(_ACCENTS)


def _purchase_title(po: PurchaseOrder) -> str:
    """Intitulé de l'achat dans Boond : la référence du bon de commande, puis la mission."""
    return " - ".join(part for part in (po.display_reference, po.mission_title) if part)


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
