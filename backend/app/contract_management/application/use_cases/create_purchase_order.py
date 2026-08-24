"""Use case: Create the first purchase order of a mission from a Boond positioning."""

from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.application.boond_parsing import (
    parse_date,
    to_decimal,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    PositioningNotFoundError,
    PositioningStateMismatchError,
    PurchaseOrderAlreadyExistsError,
)

logger = structlog.get_logger()

# Clé de configuration runtime (table `app_settings`) : état du positionnement
# Boond qui ouvre un bon de commande. Paramétrable parce que les états Boond
# sont définis par l'administrateur du CRM, pas par l'API.
TRIGGER_STATE_SETTING_KEY = "bdc_trigger_positioning_state"

# État 7 « Gagné attente contrat » : le client a dit oui, il ne reste que la
# contractualisation. Repli si la clé n'est pas renseignée.
DEFAULT_TRIGGER_STATE = 7


class CreatePurchaseOrderFromPositioningUseCase:
    """Ouvre le premier bon de commande d'une mission depuis un positionnement.

    Sert les deux portes d'entrée : le webhook positionnement (automatique) et
    la saisie manuelle de l'ADV. Dans les deux cas la lecture du positionnement
    Boond est la même, l'état est contrôlé de la même façon, et le bon de
    commande naît **sans fournisseur** — un positionnement dit quel consultant
    travaille sur quel besoin, jamais par quelle société il est porté. C'est
    l'ADV qui rattache ensuite le fournisseur.
    """

    def __init__(
        self,
        purchase_order_repository,
        crm_service,
        company_repository=None,
        user_repository=None,
        settings_service=None,
    ) -> None:
        self._po_repo = purchase_order_repository
        self._crm = crm_service
        self._company_repo = company_repository
        self._user_repo = user_repository
        self._settings = settings_service

    async def execute(
        self, positioning_id: int, *, created_by: UUID | None = None
    ) -> PurchaseOrder:
        """Execute the use case.

        Args:
            positioning_id: Boond positioning ID.
            created_by: Bobby user at the origin of the creation (manual entry).

        Returns:
            The created purchase order, in DRAFT and awaiting its supplier.

        Raises:
            PositioningNotFoundError: If Boond does not know this positioning.
            PositioningStateMismatchError: If the positioning is not in the
                state that opens a purchase order.
            PurchaseOrderAlreadyExistsError: If a live purchase order already
                exists for this positioning.
        """
        positioning = await self._crm.get_positioning(positioning_id)
        if not positioning:
            raise PositioningNotFoundError(positioning_id)

        expected_state = await self._trigger_state()
        if positioning.get("state") != expected_state:
            raise PositioningStateMismatchError(
                positioning_id, positioning.get("state"), expected_state
            )

        # Idempotence : rejouer le webhook ne crée pas un second bon de commande.
        existing = await self._po_repo.get_by_positioning_id(positioning_id)
        if existing:
            raise PurchaseOrderAlreadyExistsError(positioning_id, existing.reference)

        # Le positionnement suffit : son bloc `included` porte le besoin avec
        # son commercial, son client et son agence, le projet, et le consultant.
        # Lire en plus le besoin, la prestation et le candidat n'y ajoutait rien.
        company_id = await self._resolve_company(positioning.get("agency_id"))
        commercial_email = await self._resolve_commercial(positioning)

        # Le numéro définitif n'est attribué qu'à la génération du document :
        # un brouillon abandonné ne doit pas trouer la séquence.
        reference = await self._po_repo.get_next_provisional_reference()

        purchase_order = PurchaseOrder(
            provisional_reference=reference,
            company_id=company_id,
            boond_positioning_id=positioning_id,
            boond_need_id=positioning.get("need_id"),
            boond_project_id=positioning.get("project_id"),
            # Un candidat que Boond a déjà converti porte sa ressource : la
            # retenir évite d'en créer une seconde au report.
            boond_consultant_id=positioning.get("resource_id") or positioning.get("candidate_id"),
            boond_consultant_type=(
                "resource" if positioning.get("resource_id") else positioning.get("consultant_type")
            ),
            consultant_first_name=positioning.get("consultant_first_name") or None,
            consultant_last_name=positioning.get("consultant_last_name") or None,
            client_name=positioning.get("client_name") or None,
            mission_title=positioning.get("need_title") or None,
            # La prestation prime sur le positionnement quand elle existe :
            # elle porte les conditions négociées. Le positionnement sert de
            # repli — il connaît lui aussi les deux taux, les jours vendus et
            # la gratuité. `averageDailyCost` est un coût : il préremplit le
            # CJM d'achat ; `averageDailyPriceExcludingTax` est le tarif de
            # vente : il préremplit le TJM, interne.
            purchase_daily_rate=to_decimal(positioning.get("daily_rate")),
            sale_daily_rate=to_decimal(positioning.get("sale_daily_rate")),
            days_sold=to_decimal(positioning.get("quantity")),
            free_days=to_decimal(positioning.get("free_days")) or Decimal("0"),
            start_date=parse_date(positioning.get("start_date")),
            end_date=parse_date(positioning.get("end_date")),
            commercial_email=commercial_email or None,
            created_by=created_by,
        )

        saved = await self._po_repo.save(purchase_order)

        logger.info(
            "purchase_order_created_from_positioning",
            purchase_order_id=str(saved.id),
            reference=saved.display_reference,
            positioning_id=positioning_id,
            consultant=saved.consultant_name,
            missing_fields=saved.missing_fields,
        )
        return saved

    async def _trigger_state(self) -> int:
        """État de positionnement qui ouvre un bon de commande."""
        if not self._settings:
            return DEFAULT_TRIGGER_STATE
        raw = await self._settings.get(TRIGGER_STATE_SETTING_KEY, str(DEFAULT_TRIGGER_STATE))
        try:
            return int(raw)
        except (TypeError, ValueError):
            logger.warning("bdc_trigger_state_invalid", value=raw)
            return DEFAULT_TRIGGER_STATE

    async def _resolve_company(self, agency_id: object) -> UUID | None:
        """Résout la société émettrice depuis l'agence Boond du besoin."""
        if not agency_id or not self._company_repo:
            return None
        company_id = await self._company_repo.get_company_by_boond_agency_id(agency_id)
        if not company_id:
            logger.info("purchase_order_no_company_for_agency", agency_id=agency_id)
        return company_id

    async def _resolve_commercial(self, positioning: dict) -> str:
        """Email du commercial, par son identifiant Boond de responsable.

        Le positionnement ne porte que le nom du responsable, jamais son email :
        c'est l'utilisateur Bobby correspondant qui le donne. Un responsable
        sans compte Bobby laisse le champ vide — il ne sert qu'à montrer au
        commercial ses propres missions.
        """
        manager_id = positioning.get("manager_id")
        if manager_id and self._user_repo:
            try:
                user = await self._user_repo.get_by_boond_resource_id(str(manager_id))
            except Exception:
                user = None
            if user and getattr(user, "email", None):
                return str(user.email)
        return ""
