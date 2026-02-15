"""Use case: Generate a contract draft document."""

from uuid import UUID

import structlog

from app.contract_management.domain.entities.contract import Contract
from app.contract_management.domain.exceptions import (
    ComplianceBlockError,
    ContractRequestNotFoundError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class GenerateDraftUseCase:
    """Generate a contract draft DOCX and upload to S3.

    Verifies compliance (soft block unless overridden), generates
    the document using the template, uploads to S3, and creates
    a Contract entity.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        contract_generator,
        s3_service,
        settings,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._generator = contract_generator
        self._s3 = s3_service
        self._settings = settings

    async def execute(self, contract_request_id: UUID) -> Contract:
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The created Contract entity.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
            ComplianceBlockError: If compliance blocks generation.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        # Check compliance (soft block)
        if cr.third_party_id and not cr.compliance_override:
            tp = await self._tp_repo.get_by_id(cr.third_party_id)
            if tp and not tp.compliance_status.allows_contract_generation:
                raise ComplianceBlockError(
                    str(cr.third_party_id),
                    f"Statut de conformité : {tp.compliance_status.value}",
                )

        # Build template context
        tp = await self._tp_repo.get_by_id(cr.third_party_id) if cr.third_party_id else None
        template_context = self._build_context(cr, tp)

        # Generate DOCX
        docx_content = await self._generator.generate_draft(template_context)

        # Upload to S3
        s3_key = f"contracts/{cr.reference}/draft_v1.docx"
        await self._s3.upload_file(
            key=s3_key,
            content=docx_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Create Contract entity
        contract = Contract(
            contract_request_id=cr.id,
            third_party_id=cr.third_party_id or cr.id,
            reference=cr.reference,
            s3_key_draft=s3_key,
        )
        saved_contract = await self._contract_repo.save(contract)

        # Transition CR status
        cr.transition_to(ContractRequestStatus.DRAFT_GENERATED)
        await self._cr_repo.save(cr)

        logger.info(
            "contract_draft_generated",
            cr_id=str(cr.id),
            contract_id=str(saved_contract.id),
            s3_key=s3_key,
        )
        return saved_contract

    def _build_context(self, cr, tp) -> dict:
        """Build template context from contract request and third party."""
        context = {
            # Gemini company info
            "gemini_company_name": self._settings.GEMINI_COMPANY_NAME_CONTRACT,
            "gemini_legal_form": self._settings.GEMINI_LEGAL_FORM,
            "gemini_capital": self._settings.GEMINI_CAPITAL,
            "gemini_head_office": self._settings.GEMINI_HEAD_OFFICE,
            "gemini_rcs_city": self._settings.GEMINI_RCS_CITY,
            "gemini_rcs_number": self._settings.GEMINI_RCS_NUMBER,
            "gemini_representative_entity": self._settings.GEMINI_REPRESENTATIVE_ENTITY,
            "gemini_representative_quality": self._settings.GEMINI_REPRESENTATIVE_QUALITY,
            "gemini_representative_sub": self._settings.GEMINI_REPRESENTATIVE_SUB,
            "gemini_signatory_name": self._settings.GEMINI_SIGNATORY_NAME,
            # Contract details
            "reference": cr.reference,
            "daily_rate": str(cr.daily_rate) if cr.daily_rate else "",
            "start_date": cr.start_date.strftime("%d/%m/%Y") if cr.start_date else "",
            "client_name": cr.client_name or "",
            "mission_description": cr.mission_description or "",
            "mission_location": cr.mission_location or "",
        }

        # Partner info
        if tp:
            context.update({
                "partner_company_name": tp.company_name,
                "partner_legal_form": tp.legal_form,
                "partner_capital": tp.capital or "",
                "partner_head_office": tp.head_office_address,
                "partner_rcs_city": tp.rcs_city,
                "partner_rcs_number": tp.rcs_number,
                "partner_representative_name": tp.representative_name,
                "partner_representative_title": tp.representative_title,
                "partner_siren": tp.siren,
                "partner_siret": tp.siret,
            })

        # Contract config (clauses)
        if cr.contract_config:
            context.update(cr.contract_config)

        return context
