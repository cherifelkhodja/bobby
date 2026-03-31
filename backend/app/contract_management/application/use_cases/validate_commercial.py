"""Use case: Validate commercial information for a contract request."""

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
    """Command data for commercial validation.

    Simplified for contrat cadre: only type tiers + contact email.
    Consultant info is optional (may already come from Boond webhook).
    Mission-specific fields (TJM, dates, address) belong to BDC.
    """

    def __init__(
        self,
        *,
        contract_request_id: UUID,
        third_party_type: str,
        contact_email: str,
        company_id: UUID | None = None,
        consultant_civility: str | None = None,
        consultant_first_name: str | None = None,
        consultant_last_name: str | None = None,
        consultant_email: str | None = None,
        consultant_phone: str | None = None,
    ) -> None:
        self.contract_request_id = contract_request_id
        self.third_party_type = third_party_type
        self.contact_email = contact_email
        self.company_id = company_id
        self.consultant_civility = consultant_civility
        self.consultant_first_name = consultant_first_name
        self.consultant_last_name = consultant_last_name
        self.consultant_email = consultant_email
        self.consultant_phone = consultant_phone


class ValidateCommercialUseCase:
    """Apply commercial validation to a contract request.

    If the type is 'salarie', redirects to PayFit.
    Otherwise, creates a stub ThirdParty, requests documents and sends
    a magic link to the contact so they can fill in company info and
    upload compliance documents via the portal.

    For re-contractualization (trigger_type=ressource_4), reuses the
    ThirdParty from the previous contract request. Valid documents
    are already attached to the ThirdParty and don't need to be re-requested.
    """

    def __init__(
        self,
        contract_request_repository,
        third_party_repository,
        find_or_create_third_party_use_case,
        generate_magic_link_use_case=None,
        request_documents_use_case=None,
        document_repository=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._find_or_create_tp = find_or_create_third_party_use_case
        self._generate_magic_link_uc = generate_magic_link_use_case
        self._request_documents_uc = request_documents_use_case
        self._doc_repo = document_repository

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

        # Apply commercial data (simplified: type + contact only)
        cr.validate_commercial(
            third_party_type=command.third_party_type,
            contact_email=command.contact_email,
        )

        # Apply company_id if provided
        if command.company_id is not None:
            cr.company_id = command.company_id

        # Apply consultant fields (update only if provided, keep Boond defaults)
        if command.consultant_civility is not None:
            cr.consultant_civility = command.consultant_civility
        if command.consultant_first_name is not None:
            cr.consultant_first_name = command.consultant_first_name
        if command.consultant_last_name is not None:
            cr.consultant_last_name = command.consultant_last_name
        if command.consultant_email is not None:
            cr.consultant_email = command.consultant_email
        if command.consultant_phone is not None:
            cr.consultant_phone = command.consultant_phone

        # Re-contractualization (ressource_4): reuse existing ThirdParty
        if cr.trigger_type == "ressource_4" and cr.previous_contract_request_id:
            cr = await self._handle_recontractualization(cr, command)
        elif self._generate_magic_link_uc and self._request_documents_uc:
            # Standard flow: create stub ThirdParty, request docs, send magic link
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

        # Documents are created later when the tiers submits the portal
        # company-info form (entity_category determines ei vs societe list).

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

    async def _handle_recontractualization(self, cr, command: ValidateCommercialCommand):
        """Handle re-contractualization: reuse ThirdParty from previous CR.

        For resource state 4 (contract expired, same company):
        - Reuse the existing ThirdParty (same SIREN, same company)
        - Valid documents are already attached to the ThirdParty
        - Only expired/rejected documents need to be re-requested
        - Send magic link for any missing documents
        """
        from app.third_party.application.use_cases.generate_magic_link import (
            GenerateMagicLinkCommand,
        )

        previous_cr = await self._cr_repo.get_by_id(cr.previous_contract_request_id)
        if not previous_cr or not previous_cr.third_party_id:
            # Fallback to standard flow if no previous ThirdParty
            logger.warning(
                "recontractualization_no_previous_tp",
                cr_id=str(cr.id),
                previous_cr_id=str(cr.previous_contract_request_id),
            )
            if self._generate_magic_link_uc and self._request_documents_uc:
                return await self._initiate_document_collection(cr, command)
            return cr

        # Reuse the same ThirdParty
        cr.third_party_id = previous_cr.third_party_id
        logger.info(
            "recontractualization_reusing_third_party",
            cr_id=str(cr.id),
            third_party_id=str(previous_cr.third_party_id),
        )

        # Check if there are expired/rejected documents that need re-requesting
        has_missing_docs = False
        if self._doc_repo:
            from datetime import datetime

            from app.vigilance.domain.value_objects.document_status import DocumentStatus

            docs = await self._doc_repo.list_by_third_party(cr.third_party_id)
            for doc in docs:
                if doc.status in (
                    DocumentStatus.EXPIRED,
                    DocumentStatus.REJECTED,
                    DocumentStatus.REQUESTED,
                ):
                    has_missing_docs = True
                    break
                if doc.expires_at and doc.expires_at <= datetime.utcnow():
                    has_missing_docs = True
                    break

        if has_missing_docs and self._generate_magic_link_uc:
            # Send magic link to collect missing/expired documents
            await self._generate_magic_link_uc.execute(
                GenerateMagicLinkCommand(
                    third_party_id=cr.third_party_id,
                    purpose=MagicLinkPurpose.DOCUMENT_UPLOAD,
                    email=command.contact_email,
                    contract_request_id=cr.id,
                )
            )
            cr.transition_to(ContractRequestStatus.COLLECTING_DOCUMENTS)
            logger.info(
                "recontractualization_collecting_expired_docs",
                cr_id=str(cr.id),
            )
        else:
            # All documents still valid → skip to reviewing compliance
            cr.transition_to(ContractRequestStatus.COLLECTING_DOCUMENTS)
            cr.transition_to(ContractRequestStatus.REVIEWING_COMPLIANCE)
            logger.info(
                "recontractualization_docs_valid_skipping_to_review",
                cr_id=str(cr.id),
            )

        return cr
