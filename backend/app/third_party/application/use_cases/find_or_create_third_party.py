"""Use case: Find or create a third party by SIREN."""


import structlog

from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType

logger = structlog.get_logger()


class FindOrCreateThirdPartyCommand:
    """Command data for finding or creating a third party."""

    def __init__(
        self,
        *,
        siren: str,
        company_name: str,
        legal_form: str,
        siret: str,
        rcs_city: str,
        rcs_number: str,
        head_office_address: str,
        representative_name: str,
        representative_title: str,
        contact_email: str,
        third_party_type: ThirdPartyType,
        capital: str | None = None,
        boond_provider_id: int | None = None,
    ) -> None:
        self.siren = siren
        self.company_name = company_name
        self.legal_form = legal_form
        self.siret = siret
        self.rcs_city = rcs_city
        self.rcs_number = rcs_number
        self.head_office_address = head_office_address
        self.representative_name = representative_name
        self.representative_title = representative_title
        self.contact_email = contact_email
        self.third_party_type = third_party_type
        self.capital = capital
        self.boond_provider_id = boond_provider_id


class FindOrCreateThirdPartyUseCase:
    """Find an existing third party by SIREN or create a new one.

    If a third party with the given SIREN already exists, it is returned.
    Otherwise a new one is created with PENDING compliance status.
    """

    def __init__(self, third_party_repository, insee_client=None) -> None:
        self._third_party_repo = third_party_repository
        self._insee_client = insee_client

    async def execute(self, command: FindOrCreateThirdPartyCommand) -> ThirdParty:
        """Execute the use case.

        Args:
            command: The command data with third party details.

        Returns:
            The existing or newly created third party.
        """
        existing = await self._third_party_repo.get_by_siren(command.siren)
        if existing:
            logger.info(
                "third_party_found_by_siren",
                third_party_id=str(existing.id),
                siren=command.siren,
            )
            return existing

        # Verify SIREN with INSEE if client is available
        if self._insee_client:
            insee_info = await self._insee_client.verify_siren(command.siren)
            if insee_info and not insee_info.is_active:
                from app.third_party.domain.exceptions import InvalidSirenError

                raise InvalidSirenError(
                    f"Le SIREN {command.siren} correspond à une entreprise inactive."
                )

        third_party = ThirdParty(
            company_name=command.company_name,
            legal_form=command.legal_form,
            siren=command.siren,
            siret=command.siret,
            rcs_city=command.rcs_city,
            rcs_number=command.rcs_number,
            head_office_address=command.head_office_address,
            representative_name=command.representative_name,
            representative_title=command.representative_title,
            contact_email=command.contact_email,
            type=command.third_party_type,
            capital=command.capital,
            boond_provider_id=command.boond_provider_id,
            compliance_status=ComplianceStatus.PENDING,
        )

        saved = await self._third_party_repo.save(third_party)
        logger.info(
            "third_party_created",
            third_party_id=str(saved.id),
            siren=command.siren,
            type=command.third_party_type.value,
        )
        return saved
