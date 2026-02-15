"""Use case: Send contract for electronic signature via YouSign."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractNotFoundError,
    ContractRequestNotFoundError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class SendForSignatureUseCase:
    """Convert draft to PDF and send for signature via YouSign.

    Downloads the DOCX draft from S3, converts to PDF using LibreOffice
    headless, uploads to YouSign, creates a signature procedure, and
    transitions the CR to SENT_FOR_SIGNATURE.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        s3_service,
        signature_service,
        settings,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._s3 = s3_service
        self._signature = signature_service
        self._settings = settings

    async def execute(self, contract_request_id: UUID):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            ContractNotFoundError: If no contract exists for the request.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        contracts = await self._contract_repo.list_by_contract_request(cr.id)
        if not contracts:
            raise ContractNotFoundError(str(contract_request_id))

        contract = contracts[-1]  # Latest version

        tp = await self._tp_repo.get_by_id(cr.third_party_id) if cr.third_party_id else None
        if not tp:
            raise ContractRequestNotFoundError(str(contract_request_id))

        # Download DOCX from S3
        docx_content = await self._s3.download_file(contract.s3_key_draft)

        # Convert DOCX to PDF using LibreOffice headless
        pdf_content = await self._convert_to_pdf(docx_content, contract.reference)

        # Upload PDF to S3 as well
        pdf_s3_key = contract.s3_key_draft.replace(".docx", ".pdf")
        await self._s3.upload_file(
            key=pdf_s3_key,
            content=pdf_content,
            content_type="application/pdf",
        )

        # Determine signers
        partner_email = cr.contractualization_contact_email or tp.contact_email
        gemini_signatory = self._settings.GEMINI_SIGNATORY_NAME

        # Create YouSign procedure
        procedure_id = await self._signature.create_procedure(
            document_content=pdf_content,
            document_name=f"Contrat_{contract.reference}.pdf",
            signers=[
                {
                    "name": tp.representative_name,
                    "email": partner_email,
                    "role": "partner",
                },
                {
                    "name": gemini_signatory,
                    "email": self._settings.SMTP_FROM if hasattr(self._settings, "SMTP_FROM") else "",
                    "role": "gemini",
                },
            ],
        )

        # Update contract with YouSign info
        contract.yousign_procedure_id = procedure_id
        contract.yousign_status = "active"
        await self._contract_repo.save(contract)

        # Transition CR status
        cr.transition_to(ContractRequestStatus.SENT_FOR_SIGNATURE)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_sent_for_signature",
            cr_id=str(saved.id),
            contract_id=str(contract.id),
            yousign_procedure_id=procedure_id,
        )
        return saved

    async def _convert_to_pdf(self, docx_content: bytes, reference: str) -> bytes:
        """Convert DOCX to PDF using LibreOffice headless.

        Args:
            docx_content: Raw DOCX file content.
            reference: Contract reference for temp file naming.

        Returns:
            PDF file content as bytes.
        """
        import asyncio
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, f"{reference}.docx")
            with open(docx_path, "wb") as f:
                f.write(docx_content)

            process = await asyncio.create_subprocess_exec(
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmpdir,
                docx_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    "libreoffice_conversion_failed",
                    returncode=process.returncode,
                    stderr=stderr.decode(),
                )
                raise RuntimeError(
                    f"LibreOffice conversion failed: {stderr.decode()}"
                )

            pdf_path = os.path.join(tmpdir, f"{reference}.pdf")
            with open(pdf_path, "rb") as f:
                return f.read()
