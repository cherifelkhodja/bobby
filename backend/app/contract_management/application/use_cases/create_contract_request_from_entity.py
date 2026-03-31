"""Use case: Create a contract request from candidate/resource state change webhook."""

from typing import Any

import structlog

from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import WebhookDuplicateError

logger = structlog.get_logger()

# Boond candidate state 11 = "En attente de contrat"
BOOND_CANDIDATE_STATE_AWAITING_CONTRACT = 11

# Boond resource state 4 = "Attente nouveau contrat"
BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT = 4

# Boond resource state 5 = "Changement de contrat"
BOOND_RESOURCE_STATE_CONTRACT_CHANGE = 5


class CreateContractRequestFromEntityUseCase:
    """Create a contract request from a candidate or resource state change webhook.

    Handles 3 trigger types:
    - candidat_11: New consultant candidate → full contrat cadre workflow
    - ressource_4: Existing resource, contract expired → re-contractualization
    - ressource_5: Existing resource, company change → new contrat cadre

    BoondManager webhook payload format for candidate/resource updates:
    ```json
    [
      {
        "data": {
          "id": "3_abc123...",
          "type": "webhookevent",
          "relationships": {
            "dependsOn": {"id": "123", "type": "candidate"|"resource"}
          },
          "included": [
            {
              "type": "log",
              "attributes": {
                "content": {
                  "context": {"id": "123"},
                  "diff": {"state": {"old": 0, "new": 11}}
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

    async def execute(
        self,
        payload: dict[str, Any] | list,
        entity_type: str,
        expected_states: list[int],
    ) -> ContractRequest | None:
        """Execute the use case.

        Args:
            payload: Raw webhook payload from BoondManager.
            entity_type: "candidate" or "resource".
            expected_states: List of Boond states to process.

        Returns:
            The created contract request, or None if filtered out.
        """
        entries = payload if isinstance(payload, list) else [payload]

        for entry in entries:
            data = entry.get("data", entry)
            webhook_event_id = data.get("id", "")

            entity_id, webhook_state = self._parse_webhook_event(data, entity_type)

            if not entity_id:
                logger.warning(
                    "webhook_no_entity_id",
                    webhook_event_id=webhook_event_id,
                    entity_type=entity_type,
                )
                continue

            # Fetch entity info from Boond API (includes current state)
            consultant_type = entity_type  # "candidate" or "resource"
            entity_info = await self._crm.get_candidate_info(entity_id, consultant_type)
            if not entity_info:
                logger.error(
                    "boond_entity_not_found",
                    entity_id=entity_id,
                    entity_type=entity_type,
                )
                continue

            # Determine actual state: prefer API state, fallback to webhook diff
            new_state = entity_info.get("state") if entity_info.get("state") is not None else webhook_state

            logger.info(
                "webhook_entity_state_resolved",
                webhook_event_id=webhook_event_id,
                entity_type=entity_type,
                entity_id=entity_id,
                api_state=entity_info.get("state"),
                webhook_state=webhook_state,
                resolved_state=new_state,
            )

            # Filter: only process expected states
            if new_state not in expected_states:
                logger.info(
                    "webhook_entity_state_filtered",
                    entity_id=entity_id,
                    entity_type=entity_type,
                    state=new_state,
                    expected_states=expected_states,
                )
                continue

            # Determine trigger type
            trigger_type = self._resolve_trigger_type(entity_type, new_state)

            # Idempotence check
            event_id = f"{entity_type}_state_{entity_id}_{new_state}"
            if await self._webhook_repo.exists(event_id):
                logger.info("webhook_duplicate_event", event_id=event_id)
                raise WebhookDuplicateError(event_id)

            # Generate provisional reference
            reference = await self._cr_repo.get_next_provisional_reference()

            # Build contract request
            cr = ContractRequest(
                provisional_reference=reference,
                trigger_type=trigger_type,
                boond_candidate_id=entity_id if entity_type == "candidate" else None,
                boond_resource_id=entity_id if entity_type == "resource" else None,
                boond_consultant_type=consultant_type,
                consultant_civility=entity_info.get("civility"),
                consultant_first_name=entity_info.get("first_name"),
                consultant_last_name=entity_info.get("last_name"),
                consultant_email=entity_info.get("email"),
                consultant_phone=entity_info.get("phone"),
            )

            # For re-contractualization, find previous contract request
            if trigger_type in ("ressource_4", "ressource_5"):
                previous_cr = await self._cr_repo.get_latest_by_resource_id(entity_id)
                if previous_cr:
                    cr.previous_contract_request_id = previous_cr.id
                    # Pre-fill commercial email from previous CR
                    if previous_cr.commercial_email:
                        cr.commercial_email = previous_cr.commercial_email

            saved = await self._cr_repo.save(cr)

            # Save webhook event for idempotence
            await self._webhook_repo.save(
                event_id=event_id,
                event_type=f"{entity_type}_state_update",
                payload=entry,
            )

            # Send notification email if we have a commercial contact
            if cr.commercial_email:
                try:
                    contract_link = f"{self._frontend_url}/contracts/{saved.id}"
                    await self._email_service.send_commercial_validation_request(
                        to=cr.commercial_email,
                        commercial_name="",
                        contract_ref=reference,
                        link=contract_link,
                    )
                except Exception as email_exc:
                    logger.error(
                        "commercial_validation_email_failed",
                        error=str(email_exc),
                        cr_id=str(saved.id),
                    )

            logger.info(
                "contract_request_created_from_entity",
                cr_id=str(saved.id),
                reference=reference,
                trigger_type=trigger_type,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            return saved

        return None

    @staticmethod
    def _resolve_trigger_type(entity_type: str, state: int) -> str:
        """Map entity type + state to trigger type."""
        if entity_type == "candidate" and state == BOOND_CANDIDATE_STATE_AWAITING_CONTRACT:
            return "candidat_11"
        if entity_type == "resource" and state == BOOND_RESOURCE_STATE_AWAITING_NEW_CONTRACT:
            return "ressource_4"
        if entity_type == "resource" and state == BOOND_RESOURCE_STATE_CONTRACT_CHANGE:
            return "ressource_5"
        return f"{entity_type}_{state}"

    @staticmethod
    def _parse_webhook_event(
        data: dict[str, Any], expected_entity_type: str
    ) -> tuple[int | None, int | None]:
        """Parse a BoondManager webhook event for candidate/resource state change.

        Args:
            data: The "data" object from the webhook payload.
            expected_entity_type: "candidate" or "resource".

        Returns:
            Tuple of (entity_id, new_state). Either may be None.
        """
        data_type = data.get("type", "")

        if data_type == "webhookevent":
            relationships = data.get("relationships", {})
            depends_on = relationships.get("dependsOn", {})
            entity_type = depends_on.get("type", "")
            entity_id_str = str(depends_on.get("id", ""))

            if entity_type != expected_entity_type or not entity_id_str:
                return None, None

            try:
                entity_id = int(entity_id_str)
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

            return entity_id, new_state

        # Fallback: direct entity data (manual test)
        attributes = data.get("attributes", {})
        try:
            entity_id = int(data.get("id", 0))
        except (ValueError, TypeError):
            return None, None
        state = attributes.get("state")
        return entity_id if entity_id else None, state
