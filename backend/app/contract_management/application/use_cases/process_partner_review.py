"""Use case: Process partner review of contract draft."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class ProcessPartnerReviewUseCase:
    """Process the partner's review decision on a contract draft.

    If approved, transitions to PARTNER_APPROVED.
    If changes requested, transitions to PARTNER_REQUESTED_CHANGES and notifies ADV.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        email_service,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._email_service = email_service

    async def execute(
        self,
        contract_request_id: UUID,
        approved: bool,
        comments: str | None = None,
    ):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.
            approved: True if partner approves, False if changes requested.
            comments: Partner comments (required if not approved).

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if approved:
            cr.transition_to(ContractRequestStatus.PARTNER_APPROVED)
            logger.info("partner_approved_contract", cr_id=str(cr.id))
        else:
            cr.transition_to(ContractRequestStatus.PARTNER_REQUESTED_CHANGES)

            # Save partner comments on the contract
            contract = await self._contract_repo.get_by_request_id(cr.id)
            if contract:
                contract.partner_comments = comments
                await self._contract_repo.save(contract)

            # Notify ADV
            if comments:
                await self._email_service.send_contract_changes_requested(
                    to=cr.commercial_email,
                    contract_ref=cr.reference,
                    comments=comments,
                )

            logger.info(
                "partner_requested_changes",
                cr_id=str(cr.id),
                comments=comments,
            )

        saved = await self._cr_repo.save(cr)
        return saved
