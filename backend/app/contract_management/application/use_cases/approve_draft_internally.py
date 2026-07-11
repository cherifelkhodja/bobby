"""Use case: ADV approves the contract draft on the partner's behalf."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class ApproveDraftInternallyUseCase:
    """Approve the draft internally (fully manual flow, no partner review).

    Mirrors the partner-approval branch of ``ProcessPartnerReviewUseCase`` but is
    triggered by an ADV/admin instead of the portal: it transitions the request to
    PARTNER_APPROVED, assigns the definitive reference (XXX-CC-NNNN) and regenerates
    the draft with it. Allowed from DRAFT_GENERATED (draft not yet sent) or
    DRAFT_SENT_TO_PARTNER (sent, but the ADV approves on the partner's behalf).

    After this, the contract follows the normal signature flow, which is already
    ADV-side (signature checklist upload + mark-as-signed) — so the partner is
    never solicited.
    """

    _ALLOWED_FROM = frozenset(
        {
            ContractRequestStatus.DRAFT_GENERATED,
            ContractRequestStatus.DRAFT_SENT_TO_PARTNER,
        }
    )

    def __init__(self, contract_request_repository, draft_regenerator=None) -> None:
        self._cr_repo = contract_request_repository
        self._draft_regenerator = draft_regenerator

    async def execute(self, contract_request_id: UUID):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated (PARTNER_APPROVED) contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            InvalidContractStatusError: If the current status doesn't allow it.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if cr.status not in self._ALLOWED_FROM:
            raise InvalidContractStatusError(
                cr.status.value, ContractRequestStatus.PARTNER_APPROVED.value
            )

        cr.transition_to(ContractRequestStatus.PARTNER_APPROVED)

        # Assign the definitive reference (XXX-CC-NNNN) if still provisional.
        if not cr.reference or cr.reference.startswith("PROV-"):
            company_code = None
            if cr.company_id:
                company_code = await self._cr_repo.get_company_code(cr.company_id)
            cr.reference = await self._cr_repo.get_next_reference(company_code)

        # Regenerate the draft PDF with the final reference (best-effort).
        if self._draft_regenerator:
            try:
                await self._draft_regenerator.regenerate(cr)
            except Exception as exc:
                logger.warning(
                    "internal_approval_draft_regeneration_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

        saved = await self._cr_repo.save(cr)
        logger.info(
            "draft_approved_internally",
            cr_id=str(saved.id),
            final_reference=saved.reference,
        )
        return saved
