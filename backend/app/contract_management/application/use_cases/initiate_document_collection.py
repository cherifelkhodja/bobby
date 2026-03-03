"""Use case: Initiate document collection for a contract request."""

from datetime import datetime
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.third_party.application.use_cases.find_or_create_third_party import (
    FindOrCreateThirdPartyCommand,
)
from app.third_party.application.use_cases.generate_magic_link import (
    GenerateMagicLinkCommand,
)
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType

logger = structlog.get_logger()


class InitiateDocumentCollectionCommand:
    """Command data for initiating document collection."""

    def __init__(
        self,
        *,
        contract_request_id: UUID,
        siren: str,
        company_name: str,
        legal_form: str,
        siret: str,
        rcs_city: str,
        rcs_number: str,
        head_office_address: str,
        representative_name: str,
        representative_title: str,
        capital: str | None = None,
        boond_provider_id: int | None = None,
    ) -> None:
        self.contract_request_id = contract_request_id
        self.siren = siren
        self.company_name = company_name
        self.legal_form = legal_form
        self.siret = siret
        self.rcs_city = rcs_city
        self.rcs_number = rcs_number
        self.head_office_address = head_office_address
        self.representative_name = representative_name
        self.representative_title = representative_title
        self.capital = capital
        self.boond_provider_id = boond_provider_id


class InitiateDocumentCollectionUseCase:
    """Initiate document collection for a contract request.

    Finds or creates the third party by SIREN, creates the required vigilance
    document stubs, sends the document collection email to the contact email
    already stored on the contract request, and transitions the CR to
    COLLECTING_DOCUMENTS.

    Can also be called again from COLLECTING_DOCUMENTS or COMPLIANCE_BLOCKED
    to re-send the portal link (e.g., when the previous link expired).
    """

    ALLOWED_STATUSES = frozenset(
        {
            ContractRequestStatus.COMMERCIAL_VALIDATED,
            ContractRequestStatus.COLLECTING_DOCUMENTS,
            ContractRequestStatus.COMPLIANCE_BLOCKED,
        }
    )

    def __init__(
        self,
        contract_request_repository,
        find_or_create_third_party_use_case,
        request_documents_use_case,
        generate_magic_link_use_case,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._find_or_create_tp = find_or_create_third_party_use_case
        self._request_documents = request_documents_use_case
        self._generate_magic_link = generate_magic_link_use_case

    async def execute(self, command: InitiateDocumentCollectionCommand):
        """Execute the use case.

        Args:
            command: The command data with third party legal identity.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            InvalidContractStatusError: If the CR is not in an allowed status.
            ValueError: If the contact email is missing on the CR.
        """
        cr = await self._cr_repo.get_by_id(command.contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(command.contract_request_id))

        if cr.status not in self.ALLOWED_STATUSES:
            raise InvalidContractStatusError(
                cr.status.value,
                "commercial_validated / collecting_documents / compliance_blocked",
            )

        contact_email = cr.contractualization_contact_email
        if not contact_email:
            raise ValueError(
                "L'email de contact n'est pas renseigné sur la demande de contrat. "
                "Veuillez compléter la validation commerciale d'abord."
            )

        # Resolve third party type from CR
        tp_type = ThirdPartyType(cr.third_party_type)

        # Find or create the third party (idempotent by SIREN)
        third_party = await self._find_or_create_tp.execute(
            FindOrCreateThirdPartyCommand(
                siren=command.siren,
                company_name=command.company_name,
                legal_form=command.legal_form,
                siret=command.siret,
                rcs_city=command.rcs_city,
                rcs_number=command.rcs_number,
                head_office_address=command.head_office_address,
                representative_name=command.representative_name,
                representative_title=command.representative_title,
                contact_email=contact_email,
                third_party_type=tp_type,
                capital=command.capital,
                boond_provider_id=command.boond_provider_id,
            )
        )

        # Link the third party to the CR
        if cr.third_party_id != third_party.id:
            cr.third_party_id = third_party.id
            cr.updated_at = datetime.utcnow()

        # Create required document stubs (idempotent — skips already active docs)
        await self._request_documents.execute(third_party.id)

        # Send the portal magic link to the contact email on the CR
        await self._generate_magic_link.execute(
            GenerateMagicLinkCommand(
                third_party_id=third_party.id,
                purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
                email=contact_email,
            )
        )

        # Transition to COLLECTING_DOCUMENTS if not already there
        if cr.status != ContractRequestStatus.COLLECTING_DOCUMENTS:
            cr.transition_to(ContractRequestStatus.COLLECTING_DOCUMENTS)

        saved = await self._cr_repo.save(cr)

        logger.info(
            "document_collection_initiated",
            cr_id=str(saved.id),
            third_party_id=str(third_party.id),
            contact_email=contact_email,
        )
        return saved
