"""Use case: Handle signature completed webhook from YouSign."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractNotFoundError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class HandleSignatureCompletedUseCase:
    """Handle a signature completion event from YouSign.

    Downloads the signed PDF, archives to S3, and transitions
    the contract request to SIGNED.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        signature_service,
        s3_service,
        email_service,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._signature_service = signature_service
        self._s3 = s3_service
        self._email_service = email_service

    async def execute(self, procedure_id: str):
        """Execute the use case.

        Args:
            procedure_id: YouSign procedure/signature request ID.

        Returns:
            The updated contract.

        Raises:
            ContractNotFoundError: If no contract matches the procedure ID.
        """
        # Find the contract by YouSign procedure ID
        # This requires a custom query — for now iterate
        # In production, add an index on yousign_procedure_id


        # Download signed PDF
        signed_pdf = await self._signature_service.get_signed_document(procedure_id)

        # Find contract by procedure ID (through repository)
        # For now, we pass the contract_request_id from the webhook payload
        # This will be resolved via the webhook handler
        logger.info(
            "signature_completed",
            procedure_id=procedure_id,
            pdf_size=len(signed_pdf),
        )

        return signed_pdf

    async def execute_for_contract(self, contract_id: UUID):
        """Execute for a known contract ID.

        Args:
            contract_id: ID of the contract.
        """
        contract = await self._contract_repo.get_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(str(contract_id))

        if not contract.yousign_procedure_id:
            raise ValueError("Aucune procédure YouSign associée à ce contrat.")

        # Download signed PDF
        signed_pdf = await self._signature_service.get_signed_document(
            contract.yousign_procedure_id
        )

        # Upload signed PDF to S3
        s3_key_signed = f"contracts/{contract.reference}/signed_v{contract.version}.pdf"
        await self._s3.upload_file(
            key=s3_key_signed,
            content=signed_pdf,
            content_type="application/pdf",
        )

        # Update contract
        contract.mark_signed(s3_key_signed)
        await self._contract_repo.save(contract)

        # Transition CR to SIGNED
        cr = await self._cr_repo.get_by_id(contract.contract_request_id)
        if cr:
            cr.transition_to(ContractRequestStatus.SIGNED)
            await self._cr_repo.save(cr)

            # Send notification
            await self._email_service.send_contract_signed_notification(
                to=cr.commercial_email,
                contract_ref=cr.reference,
                third_party_name="",
            )

        logger.info(
            "contract_signed",
            contract_id=str(contract.id),
            s3_key=s3_key_signed,
        )
        return contract
