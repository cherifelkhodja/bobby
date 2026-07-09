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
        company_email_resolver=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._signature_service = signature_service
        self._s3 = s3_service
        self._email_service = email_service
        self._company_email_resolver = company_email_resolver

    async def execute_for_contract(self, contract_id: UUID):
        """Execute for a known contract ID.

        Télécharge le PDF signé, l'archive sur S3 et fait passer la demande
        de contrat en SIGNED. Idempotent : ne fait rien si la signature a déjà
        été enregistrée (via ce webhook ou via le flux manuel mark-as-signed),
        afin de ne pas entrer en conflit avec ce dernier.

        Args:
            contract_id: ID of the contract.
        """
        contract = await self._contract_repo.get_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(str(contract_id))

        if not contract.yousign_procedure_id:
            raise ValueError("Aucune procédure YouSign associée à ce contrat.")

        cr = await self._cr_repo.get_by_id(contract.contract_request_id)

        # Idempotence : si la signature est déjà enregistrée (contrat déjà signé
        # ou demande déjà en SIGNED), on ne fait rien (no-op).
        if contract.is_signed or (
            cr is not None and cr.status == ContractRequestStatus.SIGNED
        ):
            logger.info(
                "signature_already_processed",
                contract_id=str(contract.id),
                cr_status=cr.status.value if cr else None,
            )
            return contract

        # Sécurité : ne transitionne que depuis un état valide (SENT_FOR_SIGNATURE).
        # Tout autre état (ex. brouillon, déjà ACTIVE) est ignoré sans erreur.
        if cr is not None and not cr.status.can_transition_to(ContractRequestStatus.SIGNED):
            logger.warning(
                "signature_unexpected_cr_status",
                contract_id=str(contract.id),
                cr_status=cr.status.value,
            )
            return contract

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

        # Transition CR to SIGNED (cr déjà chargée plus haut)
        if cr:
            cr.transition_to(ContractRequestStatus.SIGNED)
            await self._cr_repo.save(cr)

            # Send notification
            _from_email, _company_name = None, None
            if self._company_email_resolver and cr.company_id:
                try:
                    _from_email, _company_name = await self._company_email_resolver(cr.company_id)
                except Exception:
                    pass
            await self._email_service.send_contract_signed_notification(
                to=cr.commercial_email,
                contract_ref=cr.display_reference,
                third_party_name="",
                from_email=_from_email,
                company_name=_company_name,
            )

        logger.info(
            "contract_signed",
            contract_id=str(contract.id),
            s3_key=s3_key_signed,
        )
        return contract
