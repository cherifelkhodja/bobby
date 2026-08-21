"""Use case: Create a supplier dossier (contrat cadre) from scratch."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.contract_management.application.use_cases.validate_commercial import (
    ValidateCommercialCommand,
)
from app.contract_management.domain.entities.contract_request import ContractRequest

logger = structlog.get_logger()

TRIGGER_TYPE = "supplier_manual"


def siren_from_siret(siret: str | None) -> str | None:
    """Extract the SIREN (9 first digits) from a SIRET, or None.

    Les séparateurs saisis à la main (espaces, points) sont ignorés.
    """
    if not siret:
        return None
    digits = "".join(c for c in siret if c.isdigit())
    return digits[:9] if len(digits) >= 9 else None


@dataclass
class SupplierDossierCommand:
    """Data for creating a supplier dossier."""

    third_party_type: str
    contact_email: str
    company_id: UUID | None = None
    siret: str | None = None
    commercial_email: str = ""
    # Mode de collecte, choisi dès la création : portail magic link (défaut) ou
    # saisie par l'ADV. `skip_documents` va plus loin — aucune vigilance
    # documentaire dans Bobby (traitée hors outil).
    notify_third_party: bool = True
    skip_documents: bool = False
    # Rattachement explicite à une fiche fournisseur existante, choisi par
    # l'ADV après la recherche SIRET.
    reuse_third_party_id: UUID | None = None
    # Contexte d'expédition des emails (société émettrice), résolu par la route.
    from_email: str | None = None
    company_name: str | None = None


class CreateSupplierDossierUseCase:
    """Ouvre un dossier de contractualisation pour un fournisseur.

    Point d'entrée du workflow cadre depuis Bobby : aucun consultant, aucun
    positionnement, aucun webhook. L'ADV saisit l'essentiel (type de tiers,
    contact, société émettrice, mode de collecte) et la demande part
    directement en collecte de documents.

    Le dossier réutilise la fiche fournisseur existante quand le SIRET saisi
    correspond à un tiers déjà connu : ses documents de vigilance encore
    valides restent acquis, au lieu d'être redemandés sur une fiche en double.
    """

    def __init__(
        self,
        contract_request_repository,
        third_party_repository,
        validate_commercial_use_case,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._tp_repo = third_party_repository
        self._validate_commercial = validate_commercial_use_case

    async def execute(self, command: SupplierDossierCommand) -> ContractRequest:
        """Execute the use case.

        Returns:
            The created contract request, already advanced past commercial
            validation (collecte de documents, ou revue de conformité si le
            dépôt est ignoré).
        """
        third_party_id = command.reuse_third_party_id
        if third_party_id is None:
            third_party_id = await self._find_existing_third_party(command.siret)

        reference = await self._cr_repo.get_next_provisional_reference()
        cr = ContractRequest(
            provisional_reference=reference,
            trigger_type=TRIGGER_TYPE,
            commercial_email=command.commercial_email or "",
            company_id=command.company_id,
            third_party_id=third_party_id,
            contractualization_contact_email=command.contact_email,
        )
        cr = await self._cr_repo.save(cr)

        logger.info(
            "supplier_dossier_created",
            cr_id=str(cr.id),
            reference=reference,
            reused_third_party=str(third_party_id) if third_party_id else None,
        )

        # La validation commerciale est faite d'un bloc avec la création : le
        # type de tiers, le contact et le mode de collecte sont déjà saisis.
        validation = ValidateCommercialCommand(
            contract_request_id=cr.id,
            third_party_type=command.third_party_type,
            contact_email=command.contact_email,
            company_id=command.company_id,
            notify_third_party=command.notify_third_party,
            skip_documents=command.skip_documents,
        )
        validation.from_email = command.from_email
        validation.company_name = command.company_name
        return await self._validate_commercial.execute(validation)

    async def _find_existing_third_party(self, siret: str | None) -> UUID | None:
        """Retrouve la fiche fournisseur portant ce SIRET, si elle existe."""
        siren = siren_from_siret(siret)
        if not siren:
            return None
        existing = await self._tp_repo.get_by_siren(siren)
        if not existing:
            return None
        logger.info(
            "supplier_dossier_reusing_third_party",
            third_party_id=str(existing.id),
            siren=siren,
        )
        return existing.id
