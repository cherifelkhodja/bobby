"""Use case: Validate commercial information for a contract request."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.value_objects.magic_link_purpose import MagicLinkPurpose
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType

logger = structlog.get_logger()


class ValidateCommercialCommand:
    """Command data for commercial validation."""

    def __init__(
        self,
        *,
        contract_request_id: UUID,
        third_party_type: str,
        daily_rate: Decimal,
        start_date: date,
        contact_email: str,
        end_date: date | None = None,
        client_name: str | None = None,
        mission_title: str | None = None,
        mission_description: str | None = None,
        consultant_civility: str | None = None,
        consultant_first_name: str | None = None,
        consultant_last_name: str | None = None,
        mission_site_name: str | None = None,
        mission_address: str | None = None,
        mission_postal_code: str | None = None,
        mission_city: str | None = None,
    ) -> None:
        self.contract_request_id = contract_request_id
        self.third_party_type = third_party_type
        self.daily_rate = daily_rate
        self.start_date = start_date
        self.end_date = end_date
        self.contact_email = contact_email
        self.client_name = client_name
        self.mission_title = mission_title
        self.mission_description = mission_description
        self.consultant_civility = consultant_civility
        self.consultant_first_name = consultant_first_name
        self.consultant_last_name = consultant_last_name
        self.mission_site_name = mission_site_name
        self.mission_address = mission_address
        self.mission_postal_code = mission_postal_code
        self.mission_city = mission_city


class ValidateCommercialUseCase:
    """Apply commercial validation to a contract request.

    If the type is 'salarie', redirects to PayFit.
    Otherwise, creates a stub ThirdParty, requests documents and sends
    a magic link to the contact so they can fill in company info and
    upload compliance documents via the portal.
    """

    def __init__(
        self,
        contract_request_repository,
        third_party_repository,
        find_or_create_third_party_use_case,
        generate_magic_link_use_case=None,
        request_documents_use_case=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._find_or_create_tp = find_or_create_third_party_use_case
        self._generate_magic_link_uc = generate_magic_link_use_case
        self._request_documents_uc = request_documents_use_case

    async def execute(self, command: ValidateCommercialCommand):
        """Execute the use case.

        Args:
            command: Commercial validation data.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
        """
        cr = await self._cr_repo.get_by_id(command.contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(command.contract_request_id))

        # Redirect salarié to PayFit
        if command.third_party_type == "salarie":
            cr.third_party_type = "salarie"
            cr.redirect_to_payfit()
            saved = await self._cr_repo.save(cr)
            logger.info(
                "contract_request_redirected_payfit",
                cr_id=str(saved.id),
            )
            return saved

        # Apply commercial data
        cr.validate_commercial(
            third_party_type=command.third_party_type,
            daily_rate=command.daily_rate,
            start_date=command.start_date,
            end_date=command.end_date,
            contact_email=command.contact_email,
            client_name=command.client_name,
            mission_title=command.mission_title,
            mission_description=command.mission_description,
        )

        # Apply consultant and address fields
        if command.consultant_civility is not None:
            cr.consultant_civility = command.consultant_civility
        if command.consultant_first_name is not None:
            cr.consultant_first_name = command.consultant_first_name
        if command.consultant_last_name is not None:
            cr.consultant_last_name = command.consultant_last_name
        if command.mission_site_name is not None:
            cr.mission_site_name = command.mission_site_name
        if command.mission_address is not None:
            cr.mission_address = command.mission_address
        if command.mission_postal_code is not None:
            cr.mission_postal_code = command.mission_postal_code
        if command.mission_city is not None:
            cr.mission_city = command.mission_city

        # Initiate document collection: create stub ThirdParty, request
        # documents and send magic link to the contact.
        if self._generate_magic_link_uc and self._request_documents_uc:
            cr = await self._initiate_document_collection(cr, command)

        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_request_commercial_validated",
            cr_id=str(saved.id),
            third_party_type=command.third_party_type,
        )
        return saved

    async def _initiate_document_collection(self, cr, command: ValidateCommercialCommand):
        """Create a stub ThirdParty, create document slots and send magic link."""
        from app.third_party.application.use_cases.generate_magic_link import (
            GenerateMagicLinkCommand,
        )

        # Reuse existing ThirdParty if already linked (re-validation case)
        if cr.third_party_id:
            stub_tp = await self._tp_repo.get_by_id(cr.third_party_id)
        else:
            stub_tp = None

        if not stub_tp:
            tp_type = ThirdPartyType(command.third_party_type)
            stub_tp = ThirdParty(
                contact_email=command.contact_email,
                type=tp_type,
            )
            stub_tp = await self._tp_repo.save(stub_tp)
            logger.info("stub_third_party_created", tp_id=str(stub_tp.id))

        cr.third_party_id = stub_tp.id

        # Create document request slots for the third party type
        await self._request_documents_uc.execute(stub_tp.id)

        # Send portal magic link to the contact email
        await self._generate_magic_link_uc.execute(
            GenerateMagicLinkCommand(
                third_party_id=stub_tp.id,
                purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
                email=command.contact_email,
                contract_request_id=cr.id,
            )
        )

        # Transition directly to collecting_documents
        cr.transition_to(ContractRequestStatus.COLLECTING_DOCUMENTS)

        return cr
