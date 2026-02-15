"""Use case: Validate commercial information for a contract request."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError

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
        client_name: str | None = None,
        mission_description: str | None = None,
        mission_location: str | None = None,
    ) -> None:
        self.contract_request_id = contract_request_id
        self.third_party_type = third_party_type
        self.daily_rate = daily_rate
        self.start_date = start_date
        self.contact_email = contact_email
        self.client_name = client_name
        self.mission_description = mission_description
        self.mission_location = mission_location


class ValidateCommercialUseCase:
    """Apply commercial validation to a contract request.

    If the type is 'salarie', redirects to PayFit.
    Otherwise, finds or creates the third party and checks compliance.
    """

    def __init__(
        self,
        contract_request_repository,
        third_party_repository,
        find_or_create_third_party_use_case,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._find_or_create_tp = find_or_create_third_party_use_case

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
            contact_email=command.contact_email,
            client_name=command.client_name,
            mission_description=command.mission_description,
            mission_location=command.mission_location,
        )

        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_request_commercial_validated",
            cr_id=str(saved.id),
            third_party_type=command.third_party_type,
        )
        return saved
