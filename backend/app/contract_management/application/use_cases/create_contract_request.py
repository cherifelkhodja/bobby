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
    """

    def __init__(
        self,
        contract_request_repository,
        webhook_event_repository,
        crm_service,
        email_service,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._webhook_repo = webhook_event_repository
        self._crm = crm_service
        self._email_service = email_service

    async def execute(self, payload: dict[str, Any]) -> ContractRequest | None:
        """Execute the use case.

        Args:
            payload: Raw webhook payload from BoondManager.

        Returns:
            The created contract request, or None if filtered out.

        Raises:
            WebhookDuplicateError: If the event was already processed.
        """
        # Parse payload — Boond sends array of updated entities
        entries = payload if isinstance(payload, list) else [payload]

        for entry in entries:
            data = entry.get("data", entry)
            attributes = data.get("attributes", {})
            positioning_id = int(data.get("id", 0))
            state = attributes.get("state")

            # Filter: only process state 7
            if state != BOOND_STATE_WON_AWAITING_CONTRACT:
                logger.info(
                    "webhook_positioning_state_filtered",
                    positioning_id=positioning_id,
                    state=state,
                )
                continue

            # Idempotence check
            event_id = f"positioning_update_{positioning_id}_{state}"
            if await self._webhook_repo.exists(event_id):
                logger.info(
                    "webhook_duplicate_event",
                    event_id=event_id,
                )
                raise WebhookDuplicateError(event_id)

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

            candidate_id = positioning_data.get("candidate_id")
            need_id = positioning_data.get("need_id")

            # Get commercial email from need manager
            commercial_email = ""
            if need_id:
                need_data = await self._crm.get_need(need_id)
                if need_data:
                    commercial_email = need_data.get("commercial_email", "")

            # Generate reference
            reference = await self._cr_repo.get_next_reference()

            # Create contract request
            cr = ContractRequest(
                reference=reference,
                boond_positioning_id=positioning_id,
                boond_candidate_id=candidate_id,
                boond_need_id=need_id,
                commercial_email=commercial_email,
                daily_rate=positioning_data.get("daily_rate"),
                start_date=positioning_data.get("start_date"),
            )

            saved = await self._cr_repo.save(cr)

            # Save webhook event for idempotence
            await self._webhook_repo.save(
                event_id=event_id,
                event_type="positioning_update",
                payload=entry,
            )

            # Send validation request to commercial
            if commercial_email:
                await self._email_service.send_commercial_validation_request(
                    to=commercial_email,
                    commercial_name="",
                    contract_ref=reference,
                    link="",
                )

            logger.info(
                "contract_request_created",
                cr_id=str(saved.id),
                reference=reference,
                positioning_id=positioning_id,
            )
            return saved

        return None
