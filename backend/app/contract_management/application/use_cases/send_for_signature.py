"""Use case: Mark contract as sent for signature (manual process)."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


class SendForSignatureUseCase:
    """Transition contract request to SENT_FOR_SIGNATURE status.

    Simply marks the CR as sent for signature without calling any
    external signature service. The actual signing happens outside
    the system and is validated manually via the mark-as-signed endpoint.

    # NEEDS-CONFIRMATION : le câblage automatique YouSign n'est pas branché ici.
    # ``YouSignClient.create_procedure`` existe mais n'est appelé nulle part, et
    # la route de production (``routes.py``, hors périmètre modifiable) ne fournit
    # à ce use case que ``contract_request_repository`` — sans client YouSign, ni
    # ``contract_repository``, ni accès S3 au brouillon PDF à faire signer.
    # Le brancher (appel ``create_procedure`` + persistance de
    # ``yousign_procedure_id`` sur le contrat) nécessiterait de modifier la route
    # et le repository, non inclus dans le périmètre. Le flux reste donc MANUEL :
    # la signature est validée via l'endpoint ``mark-as-signed``. Côté webhook
    # YouSign, la réception est déjà sécurisée (HMAC) et idempotente : elle reste
    # un no-op tant qu'aucun ``yousign_procedure_id`` n'est associé à un contrat.
    """

    def __init__(
        self,
        contract_request_repository,
    ) -> None:
        self._cr_repo = contract_request_repository

    async def execute(self, contract_request_id: UUID):
        """Execute the use case.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated contract request.

        Raises:
            ContractRequestNotFoundError: If the contract request does not exist.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        cr.transition_to(ContractRequestStatus.SENT_FOR_SIGNATURE)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_sent_for_signature",
            cr_id=str(saved.id),
        )
        return saved
