"""Use case: Create a purchase order request (BDC) from a positioning webhook.

When a Boond positioning reaches state 7 ("Gagné attente contrat"), we create a
BDC (PurchaseOrderRequest) for the prestation. The BDC is:

- **editable** (PENDING_VALIDATION) when the consultant is already a *resource*
  attached to a supplier that has an active framework contract;
- **locked** (PENDING_FRAMEWORK_CONTRACT) otherwise — it waits until the
  supplier's framework contract is signed (see the unlock step in
  ``sync_to_boond_after_signing``).

This webhook never creates a framework ContractRequest: the framework contract
lifecycle is driven exclusively by the candidate-state-update webhook.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog

from app.contract_management.application.use_cases.create_contract_request import (
    BOOND_STATE_WON_AWAITING_CONTRACT,
    CreateContractRequestUseCase,
)
from app.contract_management.domain.entities.purchase_order_request import (
    PurchaseOrderRequest,
)
from app.contract_management.domain.exceptions import WebhookDuplicateError
from app.contract_management.domain.value_objects.purchase_order_request_status import (
    PurchaseOrderRequestStatus,
)

logger = structlog.get_logger()


class CreatePurchaseOrderRequestFromPositioningUseCase:
    """Create a BDC from a BoondManager positioning-update webhook."""

    def __init__(
        self,
        purchase_order_request_repository,
        contract_request_repository,
        webhook_event_repository,
        third_party_repository,
        framework_contract_repository,
        crm_service,
        email_service=None,
        user_repository=None,
        frontend_url: str = "",
        company_email_resolver=None,
    ) -> None:
        self._por_repo = purchase_order_request_repository
        self._cr_repo = contract_request_repository  # for company resolution + code
        self._webhook_repo = webhook_event_repository
        self._tp_repo = third_party_repository
        self._fc_repo = framework_contract_repository
        self._crm = crm_service
        self._email_service = email_service
        self._user_repo = user_repository
        self._frontend_url = frontend_url
        self._company_email_resolver = company_email_resolver

    async def execute(self, payload: dict[str, Any] | list) -> PurchaseOrderRequest | None:
        """Parse the webhook and create a BDC (or return the existing one)."""
        entries = payload if isinstance(payload, list) else [payload]

        for entry in entries:
            data = entry.get("data", entry)
            positioning_id, payload_state = CreateContractRequestUseCase._parse_webhook_event(data)

            if not positioning_id:
                logger.warning("bdc_webhook_no_positioning_id")
                continue

            # Le webhook Boond se déclenche à CHAQUE changement d'état du
            # positionnement (ex. 7→0), pas seulement à l'entrée en 7. Quand le
            # payload porte l'état (via included[].log.content.diff.state.new), on
            # filtre tôt pour éviter un appel API inutile sur les autres états.
            if payload_state is not None and payload_state != BOOND_STATE_WON_AWAITING_CONTRACT:
                logger.info(
                    "bdc_webhook_state_filtered",
                    positioning_id=positioning_id,
                    payload_state=payload_state,
                )
                continue

            # Idempotence : un seul BDC actif par positionnement.
            existing = await self._por_repo.get_by_positioning_id(positioning_id)
            if existing:
                logger.info(
                    "bdc_already_exists",
                    positioning_id=positioning_id,
                    por_id=str(existing.id),
                )
                return existing

            # Récupérer les données Boond du positionnement (consultant, besoin…).
            # Certains payloads ne portent pas l'état (cf. webhook-configuration.md) :
            # on récupère alors l'état réel via l'API et on re-vérifie.
            positioning_data = await self._crm.get_positioning(positioning_id)
            if not positioning_data:
                logger.error("bdc_boond_positioning_not_found", positioning_id=positioning_id)
                continue

            effective_state = (
                payload_state if payload_state is not None else positioning_data.get("state")
            )
            if effective_state != BOOND_STATE_WON_AWAITING_CONTRACT:
                logger.info(
                    "bdc_webhook_state_filtered_after_api",
                    positioning_id=positioning_id,
                    payload_state=payload_state,
                    actual_state=positioning_data.get("state"),
                )
                continue

            event_id = f"positioning_bdc_{positioning_id}_{effective_state}"
            if await self._webhook_repo.exists(event_id):
                logger.info("bdc_webhook_duplicate", event_id=event_id)
                raise WebhookDuplicateError(event_id)

            candidate_id = positioning_data.get("candidate_id")
            consultant_type = positioning_data.get("consultant_type")
            need_id = positioning_data.get("need_id")

            commercial_email, client_name, mission_title, company_id = (
                await self._resolve_need_context(need_id)
            )

            # Détecter le rattachement à un contrat cadre actif.
            framework_contract_id = None
            third_party_id = None
            if consultant_type == "resource" and candidate_id:
                provider_company_id = await self._crm.get_resource_provider_company_id(
                    candidate_id
                )
                if provider_company_id:
                    tp = await self._tp_repo.get_by_boond_provider_id(provider_company_id)
                    if tp:
                        fc = await self._fc_repo.get_active_by_third_party(tp.id, company_id)
                        if fc:
                            framework_contract_id = fc.id
                            third_party_id = tp.id
                        else:
                            logger.info(
                                "bdc_no_active_framework_for_supplier",
                                positioning_id=positioning_id,
                                third_party_id=str(tp.id),
                                company_id=str(company_id) if company_id else None,
                            )
                    else:
                        logger.info(
                            "bdc_no_third_party_for_provider",
                            positioning_id=positioning_id,
                            provider_company_id=provider_company_id,
                        )

            locked = framework_contract_id is None
            status = (
                PurchaseOrderRequestStatus.PENDING_FRAMEWORK_CONTRACT
                if locked
                else PurchaseOrderRequestStatus.PENDING_VALIDATION
            )

            company_code = None
            if company_id:
                try:
                    company_code = await self._cr_repo.get_company_code(company_id)
                except Exception:
                    company_code = None
            reference = await self._por_repo.get_next_reference(company_code or "GEN")

            por = PurchaseOrderRequest(
                boond_positioning_id=positioning_id,
                commercial_email=commercial_email or "",
                reference=reference,
                framework_contract_id=framework_contract_id,
                third_party_id=third_party_id,
                boond_candidate_id=candidate_id,
                boond_consultant_type=consultant_type,
                boond_need_id=need_id,
                status=status,
                client_name=client_name,
                mission_title=mission_title,
                daily_rate=self._parse_decimal(positioning_data.get("daily_rate")),
                quantity_sold=self._parse_int(positioning_data.get("quantity")),
                start_date=self._parse_date(positioning_data.get("start_date")),
                end_date=self._parse_date(positioning_data.get("end_date")),
                consultant_first_name=positioning_data.get("consultant_first_name") or None,
                consultant_last_name=positioning_data.get("consultant_last_name") or None,
            )

            saved = await self._por_repo.save(por)
            await self._webhook_repo.save(
                event_id=event_id,
                event_type="positioning_bdc",
                payload=entry,
            )

            logger.info(
                "bdc_created_from_positioning",
                positioning_id=positioning_id,
                por_id=str(saved.id),
                reference=reference,
                locked=locked,
            )

            # Un BDC verrouillé n'est pas encore actionnable : on ne notifie le
            # commercial qu'au déverrouillage (signature du contrat cadre).
            if not locked and commercial_email and self._email_service:
                await self._notify_commercial(saved, commercial_email, company_id)

            return saved

        return None

    async def _resolve_need_context(
        self, need_id: int | None
    ) -> tuple[str, str | None, str | None, Any]:
        """Resolve commercial email, client name, mission title and issuing company."""
        commercial_email = ""
        client_name = None
        mission_title = None
        company_id = None
        if not need_id:
            return commercial_email, client_name, mission_title, company_id

        need_data = await self._crm.get_need(need_id)
        if not need_data:
            return commercial_email, client_name, mission_title, company_id

        client_name = need_data.get("client_name")
        mission_title = need_data.get("title") or None

        agency_id = need_data.get("agency_id")
        if agency_id:
            try:
                company_id = await self._cr_repo.get_company_by_boond_agency_id(agency_id)
            except Exception:
                company_id = None

        manager_id = need_data.get("manager_id")
        if manager_id and self._user_repo:
            bobby_user = await self._user_repo.get_by_boond_resource_id(str(manager_id))
            if bobby_user:
                commercial_email = str(bobby_user.email)
        if not commercial_email:
            commercial_email = need_data.get("commercial_email", "")

        return commercial_email, client_name, mission_title, company_id

    async def _notify_commercial(self, por, commercial_email: str, company_id) -> None:
        """Send the validation request email for an editable BDC (best-effort)."""
        try:
            link = f"{self._frontend_url}/contracts/po/{por.id}"
            _from_email, _company_name = None, None
            if self._company_email_resolver and company_id:
                try:
                    _from_email, _company_name = await self._company_email_resolver(company_id)
                except Exception:
                    pass
            commercial_name = commercial_email.split("@")[0] if commercial_email else ""
            await self._email_service.send_commercial_validation_request(
                to=commercial_email,
                commercial_name=commercial_name,
                contract_ref=por.reference,
                link=link,
                from_email=_from_email,
                company_name=_company_name,
            )
        except Exception as exc:
            logger.warning("bdc_commercial_email_failed", por_id=str(por.id), error=str(exc))

    @staticmethod
    def _parse_decimal(raw: object) -> Decimal | None:
        if raw:
            try:
                return Decimal(str(raw))
            except (InvalidOperation, ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_int(raw: Any) -> int | None:
        if raw is not None:
            try:
                return int(raw)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_date(raw: object) -> date | None:
        if raw and isinstance(raw, str):
            try:
                return date.fromisoformat(raw[:10])
            except (ValueError, TypeError):
                return None
        if isinstance(raw, date):
            return raw
        return None
