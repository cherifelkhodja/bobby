"""Use case: Create the first purchase order of a mission from a Boond positioning."""

from uuid import UUID

import structlog

from app.contract_management.application.boond_parsing import parse_date, to_decimal
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

        need = await self._read_need(positioning.get("need_id"))
        consultant = await self._read_consultant(
            positioning.get("candidate_id"), positioning.get("consultant_type")
        )
        company_id = await self._resolve_company(need.get("agency_id"))
        commercial_email = await self._resolve_commercial(need)

        company_code = None
        if company_id and self._company_repo:
            company_code = await self._company_repo.get_company_code(company_id)
        reference = await self._po_repo.get_next_reference(company_code)

        purchase_order = PurchaseOrder(
            reference=reference,
            company_id=company_id,
            boond_positioning_id=positioning_id,
            boond_need_id=positioning.get("need_id"),
            boond_consultant_id=positioning.get("candidate_id"),
            boond_consultant_type=positioning.get("consultant_type"),
            consultant_civility=consultant.get("civility"),
            consultant_first_name=consultant.get("first_name")
            or positioning.get("consultant_first_name")
            or None,
            consultant_last_name=consultant.get("last_name")
            or positioning.get("consultant_last_name")
            or None,
            consultant_email=consultant.get("email"),
            consultant_phone=consultant.get("phone"),
            client_name=need.get("client_name") or None,
            mission_title=need.get("title") or None,
            mission_description=need.get("description") or None,
            # `averageDailyCost` est un coût : il prérempli le CJM d'achat, pas
            # le TJM de vente, qui reste à saisir par l'ADV.
            purchase_daily_rate=to_decimal(positioning.get("daily_rate")),
            days_sold=to_decimal(positioning.get("quantity")),
            start_date=parse_date(positioning.get("start_date")),
            end_date=parse_date(positioning.get("end_date")),
            commercial_email=commercial_email or None,
            created_by=created_by,
        )

        saved = await self._po_repo.save(purchase_order)

        logger.info(
            "purchase_order_created_from_positioning",
            purchase_order_id=str(saved.id),
            reference=saved.reference,
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

    async def _read_need(self, need_id: object) -> dict:
        """Lit le besoin Boond ; son absence ne bloque pas la création."""
        if not need_id:
            return {}
        try:
            return await self._crm.get_need(need_id) or {}
        except Exception as exc:
            logger.warning("purchase_order_need_lookup_failed", need_id=need_id, error=str(exc))
            return {}

    async def _read_consultant(self, consultant_id: object, consultant_type: object) -> dict:
        """Lit l'identité du consultant ; son absence ne bloque pas la création."""
        if not consultant_id:
            return {}
        try:
            return await self._crm.get_candidate_info(consultant_id, consultant_type) or {}
        except Exception as exc:
            logger.warning(
                "purchase_order_consultant_lookup_failed",
                consultant_id=consultant_id,
                error=str(exc),
            )
            return {}

    async def _resolve_company(self, agency_id: object) -> UUID | None:
        """Résout la société émettrice depuis l'agence Boond du besoin."""
        if not agency_id or not self._company_repo:
            return None
        company_id = await self._company_repo.get_company_by_boond_agency_id(agency_id)
        if not company_id:
            logger.info("purchase_order_no_company_for_agency", agency_id=agency_id)
        return company_id

    async def _resolve_commercial(self, need: dict) -> str:
        """Email du commercial : utilisateur Bobby d'abord, Boond en repli."""
        manager_id = need.get("manager_id")
        if manager_id and self._user_repo:
            try:
                user = await self._user_repo.get_by_boond_resource_id(str(manager_id))
            except Exception:
                user = None
            if user and getattr(user, "email", None):
                return str(user.email)
        return need.get("commercial_email") or ""
