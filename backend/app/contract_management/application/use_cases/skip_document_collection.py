"""Use case: skip (or restore) the vigilance document collection."""

from uuid import UUID

import structlog

from app.contract_management.domain.exceptions import (
    ContractRequestNotFoundError,
    InvalidContractStatusError,
)
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()

DEFAULT_SKIP_REASON = "Dépôt des documents de vigilance ignoré (saisie manuelle ADV)."


async def purge_untouched_documents(document_repository, third_party_id) -> int:
    """Supprimer les emplacements de documents jamais alimentés d'un tiers.

    Un saut de collecte ne doit pas laisser de demande fantôme dans la fiche ni
    dans le tableau de bord conformité. Seuls les emplacements encore vierges
    (statut REQUESTED, sans fichier) sont supprimés : tout document réellement
    déposé — reçu, validé, rejeté ou expiré — est conservé.

    Returns:
        Le nombre d'emplacements supprimés (0 si aucun dépôt/tiers connu).
    """
    if not (document_repository and third_party_id):
        return 0

    from app.vigilance.domain.value_objects.document_status import DocumentStatus

    documents = await document_repository.list_by_third_party(third_party_id)
    purged = 0
    for doc in documents:
        if doc.status == DocumentStatus.REQUESTED and not doc.s3_key:
            await document_repository.delete(doc.id)
            purged += 1
    return purged


class SkipDocumentCollectionUseCase:
    """Ignorer le dépôt des documents de vigilance sur une demande de contrat.

    Destiné à la saisie « en personne » : l'ADV renseigne le dossier lui-même,
    sans solliciter le fournisseur, et atteste que la vigilance documentaire est
    traitée hors Bobby. La demande est marquée `documents_skipped`, la conformité
    est levée par dérogation tracée et la collecte laisse place à la revue de
    conformité — le brouillon devient générable immédiatement.

    Les emplacements de documents jamais alimentés (statut REQUESTED sans
    fichier) sont supprimés pour ne pas laisser une collecte fantôme dans la
    fiche et le tableau de bord conformité. Les documents réellement déposés
    (reçus, validés, rejetés, expirés) sont conservés.

    L'opération est réversible via `restore=True` : la dérogation est annulée et
    les emplacements de documents sont recréés à partir de la catégorie d'entité
    du tiers.
    """

    ALLOWED_STATUSES = frozenset(
        {
            ContractRequestStatus.COLLECTING_DOCUMENTS,
            ContractRequestStatus.REVIEWING_COMPLIANCE,
            ContractRequestStatus.COMPLIANCE_BLOCKED,
        }
    )

    def __init__(
        self,
        contract_request_repository,
        document_repository=None,
        third_party_repository=None,
        request_documents_use_case=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._doc_repo = document_repository
        self._tp_repo = third_party_repository
        self._request_documents_uc = request_documents_use_case

    async def execute(
        self,
        contract_request_id: UUID,
        reason: str | None = None,
        *,
        restore: bool = False,
    ):
        """Execute the use case.

        Args:
            contract_request_id: ID de la demande de contrat.
            reason: Justification tracée du saut (ignorée si `restore`).
            restore: True pour rétablir la collecte au lieu de la sauter.

        Returns:
            La demande de contrat mise à jour.

        Raises:
            ContractRequestNotFoundError: Si la demande n'existe pas.
            InvalidContractStatusError: Si le statut ne permet pas l'opération.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ContractRequestNotFoundError(str(contract_request_id))

        if cr.status not in self.ALLOWED_STATUSES:
            raise InvalidContractStatusError(
                cr.status.value,
                "collecting_documents / reviewing_compliance / compliance_blocked",
            )

        if restore:
            cr.restore_document_collection()
            recreated = await self._recreate_document_slots(cr)
            saved = await self._cr_repo.save(cr)
            logger.info(
                "document_collection_restored",
                cr_id=str(saved.id),
                documents_recreated=recreated,
            )
            return saved

        cr.skip_document_collection((reason or "").strip() or DEFAULT_SKIP_REASON)
        purged = await purge_untouched_documents(self._doc_repo, cr.third_party_id)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "document_collection_skipped",
            cr_id=str(saved.id),
            third_party_id=str(cr.third_party_id) if cr.third_party_id else None,
            documents_purged=purged,
        )
        return saved

    async def _recreate_document_slots(self, cr) -> int:
        """Recréer les emplacements de documents (idempotent) après rétablissement.

        Nécessite que l'identité du tiers ait déjà été saisie : la liste des
        documents dépend de la catégorie d'entité (EI vs société).
        """
        if not (self._request_documents_uc and self._tp_repo and cr.third_party_id):
            return 0

        tp = await self._tp_repo.get_by_id(cr.third_party_id)
        if not tp or not tp.entity_category:
            return 0

        created = await self._request_documents_uc.execute(
            tp.id, entity_category=tp.entity_category
        )
        return len(created)
