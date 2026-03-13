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

    If approved, transitions to PARTNER_APPROVED and regenerates the draft
    with the final reference.
    If changes requested, transitions to PARTNER_REQUESTED_CHANGES and notifies ADV.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        email_service,
        draft_regenerator=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._email_service = email_service
        self._draft_regenerator = draft_regenerator

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
            # Assigner la référence définitive (format XXX-YYYY-NNNN)
            # Résoudre le code de la société émettrice liée à cette demande
            company_code = None
            if cr.company_id:
                company_code = await self._cr_repo.get_company_code(cr.company_id)
            cr.reference = await self._cr_repo.get_next_reference(company_code)
            logger.info(
                "partner_approved_contract",
                cr_id=str(cr.id),
                final_reference=cr.reference,
            )
            client_label = f" pour <strong>{cr.client_name}</strong>" if cr.client_name else ""
            await self._email_service.send_contract_progress_to_commercial(
                to=cr.commercial_email,
                contract_ref=cr.display_reference,
                step_title="Partenaire a approuvé le contrat",
                step_message=f"Le partenaire a validé le projet de contrat{client_label}. Le contrat peut maintenant être envoyé en signature.",
                step_color="#10b981",
            )

            # Regenerate the draft PDF with the final reference
            if self._draft_regenerator:
                try:
                    await self._draft_regenerator.regenerate(cr)
                    logger.info(
                        "draft_regenerated_with_final_reference",
                        cr_id=str(cr.id),
                        reference=cr.display_reference,
                    )
                except Exception as exc:
                    logger.warning(
                        "draft_regeneration_failed",
                        cr_id=str(cr.id),
                        error=str(exc),
                    )
        else:
            cr.transition_to(ContractRequestStatus.PARTNER_REQUESTED_CHANGES)

            # Attach comment to the history entry so the timeline can display it
            if comments and cr.status_history:
                cr.status_history[-1]["comment"] = comments

            # Save partner comments on the contract
            contract = await self._contract_repo.get_by_request_id(cr.id)
            if contract:
                contract.partner_comments = comments
                await self._contract_repo.save(contract)

            # Notify commercial
            await self._email_service.send_contract_progress_to_commercial(
                to=cr.commercial_email,
                contract_ref=cr.display_reference,
                step_title="Partenaire demande des modifications",
                step_message=f"Le partenaire a demandé des modifications sur le contrat"
                f"{' pour <strong>' + cr.client_name + '</strong>' if cr.client_name else ''}."
                f"{('<br><br><strong>Commentaires :</strong> ' + comments) if comments else ''}",
                step_color="#f59e0b",
            )

            logger.info(
                "partner_requested_changes",
                cr_id=str(cr.id),
                comments=comments,
            )

        saved = await self._cr_repo.save(cr)
        return saved
