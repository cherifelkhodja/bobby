"""Use case: Send contract draft to partner for review."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

logger = structlog.get_logger()


class SendDraftToPartnerUseCase:
    """Send the contract draft to the partner via magic link.

    Creates a CONTRACT_REVIEW magic link, sends email with portal URL,
    and transitions the CR to DRAFT_SENT_TO_PARTNER.
    """

    def __init__(
        self,
        contract_request_repository,
        third_party_repository,
        generate_magic_link_use_case,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._generate_magic_link = generate_magic_link_use_case

    async def execute(
        self,
        contract_request_id: UUID,
        from_email: str | None = None,
        company_name: str | None = None,
    ):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if not cr.third_party_id:
            raise ValueError("Aucun tiers associé à cette demande de contrat.")

        tp = await self._tp_repo.get_by_id(cr.third_party_id)
        if not tp:
            raise ContractRequestNotFoundError(str(contract_request_id))

        # Valider la transition AVANT tout effet de bord (génération du magic link +
        # envoi de l'email au partenaire) : un statut illégal ne doit ni générer de
        # lien ni déclencher d'envoi.
        if not cr.status.can_transition_to(ContractRequestStatus.DRAFT_SENT_TO_PARTNER):
            raise InvalidContractStatusError(
                cr.status.value, ContractRequestStatus.DRAFT_SENT_TO_PARTNER.value
            )

        email = cr.contractualization_contact_email or tp.contact_email

        # Generate magic link for contract review
        from app.third_party.application.use_cases.generate_magic_link import (
            GenerateMagicLinkCommand,
        )

        await self._generate_magic_link.execute(
            GenerateMagicLinkCommand(
                third_party_id=cr.third_party_id,
                purpose=MagicLinkPurpose.CONTRACT_REVIEW,
                email=email,
                contract_request_id=cr.id,
                from_email=from_email,
                company_name=company_name,
            )
        )

        # Transition status
        cr.transition_to(ContractRequestStatus.DRAFT_SENT_TO_PARTNER)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "draft_sent_to_partner",
            cr_id=str(saved.id),
            email=email,
        )
        return saved
