"""Use case: Push signed contract data to BoondManager."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import ContractRequestNotFoundError

logger = structlog.get_logger()


class PushToCrmUseCase:
    """Push contract data to BoondManager after signature.

    Creates or updates the provider in Boond and creates a purchase order
    (idempotent). L'archivage du CR relève du CRON : ce use case ne le tente
    que si la demande est déjà ACTIVE.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        crm_service,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service

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

        contract = await self._contract_repo.get_by_request_id(cr.id)
        if not contract:
            raise ContractRequestNotFoundError(str(contract_request_id))

        tp = None
        if cr.third_party_id:
            tp = await self._tp_repo.get_by_id(cr.third_party_id)

        # Create/update provider in Boond if no boond_provider_id
        if tp and not tp.boond_provider_id:
            provider_id = await self._crm.create_provider(
                company_name=tp.company_name,
                siren=tp.siren,
                contact_email=tp.contact_email,
            )
            tp.boond_provider_id = provider_id
            await self._tp_repo.save(tp)

        # Create purchase order in Boond (idempotent : seulement si absent, pour
        # qu'un rejeu ne crée pas un second BDC côté Boond).
        if tp and tp.boond_provider_id and cr.daily_rate and not contract.boond_purchase_order_id:
            # NEEDS-CONFIRMATION: montant = TJM seul (cf. note détaillée dans
            # BoondCrmAdapter.create_purchase_order).
            amount = float(cr.daily_rate)
            po_id = await self._crm.create_purchase_order(
                provider_id=tp.boond_provider_id,
                positioning_id=cr.boond_positioning_id,
                reference=cr.display_reference,
                amount=amount,
            )
            contract.boond_purchase_order_id = po_id
            await self._contract_repo.save(contract)

        # Le contrat cadre reste ACTIF après signature : c'est un cadre vivant qui
        # sert de base aux BDC (détection « contrat cadre actif »). L'archivage
        # est le rôle du CRON (quand plus aucun BDC actif depuis 6 mois) — on ne
        # l'archive donc PLUS ici, sinon le cadre disparaît de la détection BDC
        # dès le push CRM et les futurs BDC restent verrouillés à tort.
        saved = await self._cr_repo.save(cr)

        logger.info(
            "contract_pushed_to_crm",
            cr_id=str(saved.id),
            reference=cr.display_reference,
        )
        return saved
