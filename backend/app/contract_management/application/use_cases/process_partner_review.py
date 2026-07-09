"""Use case: Process partner review of contract draft."""

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
        company_email_resolver=None,
        internal_recipients: list[str] | None = None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._email_service = email_service
        self._draft_regenerator = draft_regenerator
        self._company_email_resolver = company_email_resolver
        # Emails des émetteurs internes (ADV/admin) à notifier en plus du commercial
        self._internal_recipients = internal_recipients or []

    def _notification_recipients(self, cr) -> list[str]:
        """Commercial + émetteurs internes (ADV/admin), dédupliqués, sans vide."""
        recipients: list[str] = []
        for addr in [cr.commercial_email, *self._internal_recipients]:
            if addr and addr not in recipients:
                recipients.append(addr)
        return recipients

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

        # Garde d'idempotence : une décision de relecture ne peut être enregistrée
        # qu'une seule fois, tant que la demande est en attente du partenaire. Tout
        # autre état (déjà approuvée, modifications déjà demandées, annulée, signée…)
        # signifie qu'il s'agit d'un rejeu → on refuse proprement au lieu de tenter
        # une transition illégale (qui remonterait en 500).
        if cr.status != ContractRequestStatus.DRAFT_SENT_TO_PARTNER:
            logger.warning(
                "partner_review_already_processed",
                cr_id=str(cr.id),
                current_status=cr.status.value,
            )
            raise InvalidContractStatusError(
                cr.status.value,
                (
                    ContractRequestStatus.PARTNER_APPROVED.value
                    if approved
                    else ContractRequestStatus.PARTNER_REQUESTED_CHANGES.value
                ),
            )

        # Resolve company email context
        _from_email, _company_name = None, None
        if self._company_email_resolver and cr.company_id:
            try:
                _from_email, _company_name = await self._company_email_resolver(cr.company_id)
            except Exception:
                pass

        if approved:
            cr.transition_to(ContractRequestStatus.PARTNER_APPROVED)
            # Assigner la référence définitive (format XXX-CC-NNNN) si pas encore fait
            if not cr.reference or cr.reference.startswith("PROV-"):
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
            for recipient in self._notification_recipients(cr):
                await self._email_service.send_contract_progress_to_commercial(
                    to=recipient,
                    contract_ref=cr.display_reference,
                    step_title="Partenaire a approuvé le contrat",
                    step_message=f"Le partenaire a validé le projet de contrat{client_label}. Le contrat peut maintenant être envoyé en signature.",
                    step_color="#10b981",
                    from_email=_from_email,
                    company_name=_company_name,
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

            # Notify commercial + émetteurs internes (ADV/admin)
            for recipient in self._notification_recipients(cr):
                await self._email_service.send_contract_progress_to_commercial(
                    to=recipient,
                    contract_ref=cr.display_reference,
                    step_title="Partenaire demande des modifications",
                    from_email=_from_email,
                    company_name=_company_name,
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
