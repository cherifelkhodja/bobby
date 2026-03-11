"""Use case: Create a contract request from Boond webhook."""

from typing import Any

import structlog

from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import WebhookDuplicateError

logger = structlog.get_logger()

# Boond positioning state 7 = "Gagné attente contrat"
BOOND_STATE_WON_AWAITING_CONTRACT = 7


class CreateContractRequestUseCase:
    """Create a contract request from a BoondManager webhook.

    Parses the webhook payload (positioning update), checks for
    idempotence, fetches Boond data, and creates a contract request.

    BoondManager webhook payload format:
    ```json
    [
      {
        "data": {
          "id": "3_abc123...",       // webhook event ID (NOT positioning ID)
          "type": "webhookevent",
          "attributes": {"type": "update", ...},
          "relationships": {
            "dependsOn": {"id": "433", "type": "positioning"},
            "log": {"id": "117497", "type": "log"}
          },
          "included": [
            {
              "id": "117497", "type": "log",
              "attributes": {
                "content": {
                  "context": {"id": "433"},
                  "diff": {"state": {"old": 0, "new": 7}}
                }
              }
            }
          ]
        }
      }
    ]
    ```
    """

    def __init__(
        self,
        contract_request_repository,
        webhook_event_repository,
        crm_service,
        email_service,
        user_repository=None,
        frontend_url: str = "",
        company_repository=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._webhook_repo = webhook_event_repository
        self._crm = crm_service
        self._email_service = email_service
        self._user_repo = user_repository
        self._frontend_url = frontend_url
        self._company_repo = company_repository

    async def execute(self, payload: dict[str, Any] | list) -> ContractRequest | None:
        """Execute the use case.

        Args:
            payload: Raw webhook payload from BoondManager (array of events).

        Returns:
            The created contract request, or None if filtered out.

        Raises:
            WebhookDuplicateError: If the event was already processed.
        """
        # Boond sends an array of webhook events
        entries = payload if isinstance(payload, list) else [payload]

        for entry in entries:
            data = entry.get("data", entry)
            webhook_event_id = data.get("id", "")
            data_type = data.get("type", "")

            # Parse depending on payload format
            positioning_id, new_state = self._parse_webhook_event(data)

            if not positioning_id:
                logger.warning(
                    "webhook_no_positioning_id",
                    webhook_event_id=webhook_event_id,
                    data_type=data_type,
                )
                continue

            logger.info(
                "webhook_parsed",
                webhook_event_id=webhook_event_id,
                positioning_id=positioning_id,
                new_state=new_state,
            )

            # Filter: only process state 7
            if new_state != BOOND_STATE_WON_AWAITING_CONTRACT:
                logger.info(
                    "webhook_positioning_state_filtered",
                    positioning_id=positioning_id,
                    state=new_state,
                )
                continue

            # Idempotence check using webhook event ID
            event_id = f"positioning_update_{positioning_id}_{new_state}"
            if await self._webhook_repo.exists(event_id):
                # Check if all CRs for this positioning are cancelled
                # If so, allow re-creation by clearing old dedup entry
                existing = await self._cr_repo.get_by_positioning_id(positioning_id)
                if existing is None:
                    # No active CR → previous one was cancelled, clear dedup
                    await self._webhook_repo.delete_by_prefix(
                        f"positioning_update_{positioning_id}_"
                    )
                    logger.info(
                        "webhook_dedup_cleared_after_cancel",
                        event_id=event_id,
                        positioning_id=positioning_id,
                    )
                else:
                    logger.info("webhook_duplicate_event", event_id=event_id)
                    raise WebhookDuplicateError(event_id)
            else:
                # Check if CR already exists for this positioning
                existing = await self._cr_repo.get_by_positioning_id(positioning_id)
                if existing:
                    logger.info(
                        "contract_request_already_exists",
                        positioning_id=positioning_id,
                        cr_id=str(existing.id),
                    )
                    return existing

            # Fetch Boond data
            positioning_data = await self._crm.get_positioning(positioning_id)
            if not positioning_data:
                logger.error(
                    "boond_positioning_not_found",
                    positioning_id=positioning_id,
                )
                continue

            logger.info(
                "boond_positioning_data",
                positioning_data=positioning_data,
            )

            candidate_id = positioning_data.get("candidate_id")
            consultant_type = positioning_data.get("consultant_type")
            need_id = positioning_data.get("need_id")

            # Get commercial info: prefer Bobby DB, fallback to Boond API
            commercial_email = ""
            commercial_name = ""
            client_name = None
            mission_title = None
            mission_description = None
            company_id = None
            if need_id:
                need_data = await self._crm.get_need(need_id)
                if need_data:
                    manager_id = need_data.get("manager_id")
                    client_name = need_data.get("client_name")
                    mission_title = need_data.get("title") or None
                    mission_description = need_data.get("description") or None

                    # Resolve société émettrice from the need's agency
                    agency_id = need_data.get("agency_id")
                    if agency_id and self._company_repo:
                        company_id = await self._company_repo.get_company_by_boond_agency_id(agency_id)
                        if company_id:
                            logger.info(
                                "company_resolved_from_agency",
                                agency_id=agency_id,
                                company_id=str(company_id),
                            )
                        else:
                            logger.info(
                                "no_company_for_agency",
                                agency_id=agency_id,
                            )

                    # Try Bobby DB first (commercial is a registered user)
                    if manager_id and self._user_repo:
                        bobby_user = await self._user_repo.get_by_boond_resource_id(str(manager_id))
                        if bobby_user:
                            commercial_email = str(bobby_user.email)
                            commercial_name = (
                                f"{bobby_user.first_name} {bobby_user.last_name}".strip()
                            )
                            logger.info(
                                "commercial_found_in_bobby",
                                boond_resource_id=manager_id,
                                email=commercial_email,
                            )

                    # Fallback to Boond API data
                    if not commercial_email:
                        commercial_email = need_data.get("commercial_email", "")
                        commercial_name = need_data.get("commercial_name", "")
                        if commercial_email:
                            logger.info(
                                "commercial_found_in_boond",
                                email=commercial_email,
                            )

            # Generate provisional reference (définitive assignée à PARTNER_APPROVED)
            reference = await self._cr_repo.get_next_provisional_reference()

            # Sanitize Boond data — empty strings must be None for DB types
            raw_daily_rate = positioning_data.get("daily_rate")
            raw_quantity = positioning_data.get("quantity")
            raw_start_date = positioning_data.get("start_date")
            raw_end_date = positioning_data.get("end_date")

            from datetime import date
            from decimal import Decimal, InvalidOperation

            daily_rate = None
            if raw_daily_rate:
                try:
                    daily_rate = Decimal(str(raw_daily_rate))
                except (InvalidOperation, ValueError, TypeError):
                    daily_rate = None

            def _parse_date(raw: object) -> date | None:
                if raw and isinstance(raw, str):
                    try:
                        return date.fromisoformat(raw[:10])
                    except (ValueError, TypeError):
                        return None
                if isinstance(raw, date):
                    return raw
                return None

            quantity_sold = None
            if raw_quantity is not None:
                try:
                    quantity_sold = int(raw_quantity)
                except (ValueError, TypeError):
                    quantity_sold = None

            start_date = _parse_date(raw_start_date)
            end_date = _parse_date(raw_end_date)

            # Fetch consultant info from Boond positioning candidate
            consultant_civility = None
            consultant_first_name = positioning_data.get("consultant_first_name") or None
            consultant_last_name = positioning_data.get("consultant_last_name") or None
            consultant_email = None
            consultant_phone = None
            if candidate_id:
                candidate_info = await self._crm.get_candidate_info(candidate_id, consultant_type)
                if candidate_info:
                    consultant_civility = candidate_info.get("civility") or None
                    consultant_first_name = candidate_info.get("first_name") or consultant_first_name
                    consultant_last_name = candidate_info.get("last_name") or consultant_last_name
                    consultant_email = candidate_info.get("email") or None
                    consultant_phone = candidate_info.get("phone") or None

            # Create contract request
            cr = ContractRequest(
                provisional_reference=reference,
                boond_positioning_id=positioning_id,
                boond_candidate_id=candidate_id,
                boond_consultant_type=consultant_type,
                boond_need_id=need_id,
                commercial_email=commercial_email or "",
                client_name=client_name,
                mission_title=mission_title,
                mission_description=mission_description,
                consultant_civility=consultant_civility,
                consultant_first_name=consultant_first_name,
                consultant_last_name=consultant_last_name,
                consultant_email=consultant_email,
                consultant_phone=consultant_phone,
                daily_rate=daily_rate,
                quantity_sold=quantity_sold,
                start_date=start_date,
                end_date=end_date,
                company_id=company_id,
            )

            saved = await self._cr_repo.save(cr)

            # Save webhook event for idempotence
            await self._webhook_repo.save(
                event_id=event_id,
                event_type="positioning_update",
                payload=entry,
            )

            # Send validation request to commercial (non-blocking: email
            # failure must never rollback the contract request creation)
            if commercial_email:
                try:
                    contract_link = f"{self._frontend_url}/contracts/{saved.id}"
                    logger.info(
                        "sending_commercial_validation_email",
                        to=commercial_email,
                        commercial_name=commercial_name,
                        contract_ref=reference,
                        link=contract_link,
                    )
                    email_sent = await self._email_service.send_commercial_validation_request(
                        to=commercial_email,
                        commercial_name=commercial_name,
                        contract_ref=reference,
                        link=contract_link,
                    )
                    logger.info(
                        "commercial_validation_email_result",
                        email_sent=email_sent,
                        to=commercial_email,
                    )
                except Exception as email_exc:
                    logger.error(
                        "commercial_validation_email_failed",
                        error=str(email_exc),
                        to=commercial_email,
                        cr_id=str(saved.id),
                    )
            else:
                logger.warning(
                    "no_commercial_email_for_notification",
                    positioning_id=positioning_id,
                    cr_id=str(saved.id),
                )

            logger.info(
                "contract_request_created",
                cr_id=str(saved.id),
                reference=reference,
                positioning_id=positioning_id,
                commercial_email=commercial_email,
            )
            return saved

        return None

    @staticmethod
    def _parse_webhook_event(data: dict[str, Any]) -> tuple[int | None, int | None]:
        """Parse a BoondManager webhook event to extract positioning ID and new state.

        BoondManager sends webhook events with type "webhookevent". The actual
        positioning ID is in relationships.dependsOn, and the state change is
        in the included log entry's content.diff.

        Args:
            data: The "data" object from the webhook payload.

        Returns:
            Tuple of (positioning_id, new_state). Either may be None.
        """
        data_type = data.get("type", "")

        if data_type == "webhookevent":
            # Extract positioning ID from relationships.dependsOn
            relationships = data.get("relationships", {})
            depends_on = relationships.get("dependsOn", {})
            entity_type = depends_on.get("type", "")
            entity_id_str = str(depends_on.get("id", ""))

            if entity_type != "positioning" or not entity_id_str:
                return None, None

            try:
                positioning_id = int(entity_id_str)
            except (ValueError, TypeError):
                return None, None

            # Extract new state from included log entry
            new_state = None
            for included in data.get("included", []):
                if included.get("type") != "log":
                    continue
                content = included.get("attributes", {}).get("content", {})
                diff = content.get("diff", {})
                state_diff = diff.get("state", {})
                if "new" in state_diff:
                    new_state = state_diff["new"]
                    break

            return positioning_id, new_state

        # Fallback: direct positioning data (e.g., from manual test)
        attributes = data.get("attributes", {})
        try:
            positioning_id = int(data.get("id", 0))
        except (ValueError, TypeError):
            return None, None
        state = attributes.get("state")
        return positioning_id if positioning_id else None, state
