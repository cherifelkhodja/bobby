"""Use case: Generate a magic link for a third party."""

from uuid import UUID

import structlog

from app.domain.exceptions import DomainError
from app.third_party.domain.entities.magic_link import MagicLink
from app.third_party.domain.exceptions import ThirdPartyNotFoundError
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose

logger = structlog.get_logger()


class MagicLinkEmailNotSentError(DomainError):
    """Levée quand l'email contenant le lien du portail n'a pas pu être envoyé.

    La ligne magic link est annulée avec la transaction englobante : l'appelant
    peut donc relancer l'envoi sans laisser de lien orphelin jamais délivré.
    """

    def __init__(self, email: str = "") -> None:
        target = f" à {email}" if email else ""
        super().__init__(
            f"L'email contenant le lien du portail n'a pas pu être envoyé{target}. "
            "Veuillez réessayer ou relancer l'envoi."
        )


class GenerateMagicLinkCommand:
    """Command data for generating a magic link."""

    def __init__(
        self,
        *,
        third_party_id: UUID,
        purpose: MagicLinkPurpose,
        email: str,
        contract_request_id: UUID | None = None,
        from_email: str | None = None,
        company_name: str | None = None,
        contract_ref: str = "",
    ) -> None:
        self.third_party_id = third_party_id
        self.purpose = purpose
        self.email = email
        self.contract_request_id = contract_request_id
        self.from_email = from_email
        self.company_name = company_name
        self.contract_ref = contract_ref


class GenerateMagicLinkUseCase:
    """Generate a new magic link for a third party.

    Revokes all existing active links for the same third party and purpose
    before creating a new one, then sends the link via email.
    """

    def __init__(
        self,
        third_party_repository,
        magic_link_repository,
        email_service,
        portal_base_url: str,
    ) -> None:
        self._third_party_repo = third_party_repository
        self._magic_link_repo = magic_link_repository
        self._email_service = email_service
        self._portal_base_url = portal_base_url

    async def execute(self, command: GenerateMagicLinkCommand) -> MagicLink:
        """Execute the use case.

        Args:
            command: The command data with link details.

        Returns:
            The newly created magic link.

        Raises:
            ThirdPartyNotFoundError: If the third party does not exist.
        """
        third_party = await self._third_party_repo.get_by_id(command.third_party_id)
        if not third_party:
            raise ThirdPartyNotFoundError(command.third_party_id)

        # Revoke existing active links for same purpose
        revoked = await self._magic_link_repo.revoke_all_for_third_party(
            third_party_id=command.third_party_id,
            purpose=command.purpose,
        )
        if revoked > 0:
            logger.info(
                "previous_magic_links_revoked",
                third_party_id=str(command.third_party_id),
                purpose=command.purpose.value,
                revoked_count=revoked,
            )

        magic_link = MagicLink(
            third_party_id=command.third_party_id,
            purpose=command.purpose,
            email_sent_to=command.email,
            contract_request_id=command.contract_request_id,
        )

        saved = await self._magic_link_repo.save(magic_link)

        # Envoi de l'email contenant le lien du portail.
        # Un échec ici ne doit JAMAIS être silencieux : sinon le tiers ne reçoit
        # jamais son lien et le workflow reste bloqué (ex. COLLECTING_DOCUMENTS)
        # sans aucune trace. On le remonte pour que la route retourne une erreur
        # exploitable et que la transaction soit annulée (lien non délivré = pas
        # de lien persisté).
        portal_url = f"{self._portal_base_url}/{saved.token}"
        try:
            if command.purpose == MagicLinkPurpose.DOCUMENT_UPLOAD:
                email_sent = await self._email_service.send_document_collection_request(
                    to=command.email,
                    third_party_name=third_party.company_name or third_party.contact_email,
                    portal_link=portal_url,
                    from_email=command.from_email,
                    company_name=command.company_name,
                )
            elif command.purpose == MagicLinkPurpose.CONTRACT_REVIEW:
                email_sent = await self._email_service.send_contract_draft_review(
                    to=command.email,
                    third_party_name=third_party.company_name,
                    contract_ref=command.contract_ref,
                    portal_link=portal_url,
                    from_email=command.from_email,
                    company_name=command.company_name,
                )
            else:
                # Aucun email associé aux autres finalités : rien à envoyer.
                email_sent = True
        except Exception as exc:
            logger.error(
                "magic_link_email_error",
                magic_link_id=str(saved.id),
                third_party_id=str(command.third_party_id),
                purpose=command.purpose.value,
                email=command.email,
                error=str(exc),
            )
            raise MagicLinkEmailNotSentError(command.email) from exc

        if not email_sent:
            logger.error(
                "magic_link_email_not_sent",
                magic_link_id=str(saved.id),
                third_party_id=str(command.third_party_id),
                purpose=command.purpose.value,
                email=command.email,
            )
            raise MagicLinkEmailNotSentError(command.email)

        logger.info(
            "magic_link_generated",
            magic_link_id=str(saved.id),
            third_party_id=str(command.third_party_id),
            purpose=command.purpose.value,
            email=command.email,
        )
        return saved
