"""Use case: Synchronise all data to BoondManager after contract signing."""

import re
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.application.boond_contacts import (
    persisted_contact_ids,
    split_supplier_contacts,
)
from app.contract_management.application.boond_mappings import (
    resource_type_of,
    state_reason_type_of,
)
from app.contract_management.application.boond_supplier import find_existing_contact_id
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()


def _format_siren(siren: str) -> str:
    """Format a SIREN number with spaces every 3 digits (e.g. '894213669' → '894 213 669')."""
    digits = re.sub(r"\D", "", siren)
    return " ".join(digits[i : i + 3] for i in range(0, len(digits), 3))


class SyncToBoondAfterSigningUseCase:
    """Synchronise all relevant data to BoondManager after contract signing.

    Executes the following steps (best-effort — individual failures are logged
    but do not abort the overall flow):

    1. Create the provider company in Boond with full legal details.
    2. Create the contacts (signataire, ADV, commercial) linked to the company.
    3. Convert the candidate to a resource (state 3) if boond_candidate_id is set.
    4a. Link the resource to the provider company + commercial contact.
    6. Transition the contract request to ACTIVE.
    """

    def __init__(
        self,
        db: AsyncSession,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        crm_service,
    ) -> None:
        self._db = db
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._crm = crm_service

    async def execute(self, contract_request_id: UUID):
        """Run the post-signing Boond sync.

        Args:
            contract_request_id: ID of the contract request.

        Returns:
            The updated (ACTIVE) contract request.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ValueError(f"Demande de contrat introuvable: {contract_request_id}")

        tp = None
        if cr.third_party_id:
            tp = await self._tp_repo.get_by_id(cr.third_party_id)

        # Fetch the issuing company to get boond_agency_id
        company = await self._get_contract_company(cr.company_id)

        # For new workflow (candidat/resource triggers), boond_resource_id is set
        resource_id: int | None = cr.boond_resource_id or cr.boond_candidate_id

        # ── Étape 1 : Création société fournisseur ─────────────────────────
        # Build formatted legal fields
        legal_status = None
        if tp and tp.legal_form and tp.capital:
            legal_status = f"{tp.legal_form} au capital de {tp.capital} €"
        registered_office = None
        if tp and tp.rcs_number and tp.rcs_city:
            formatted_siren = _format_siren(tp.rcs_number)
            registered_office = f"{formatted_siren} R.C.S. {tp.rcs_city}"

        # Une société créée à l'instant n'a aucun contact : inutile d'y
        # chercher ceux du fournisseur.
        company_created_now = False

        # Verify cached provider_id still exists in Boond
        if tp and tp.boond_provider_id:
            exists = await self._crm.verify_company_exists(tp.boond_provider_id)
            if not exists:
                logger.warning(
                    "sync_boond_provider_id_stale",
                    cr_id=str(cr.id),
                    stale_id=tp.boond_provider_id,
                )
                tp.boond_provider_id = None
            else:
                # Company exists — update with latest data
                try:
                    await self._crm.update_company_information(
                        company_id=tp.boond_provider_id,
                        postcode=tp.head_office_postal_code,
                        address=tp.head_office_street or tp.head_office_address,
                        town=tp.head_office_city,
                        country="France",
                        legal_status=legal_status,
                        registered_office=registered_office,
                        vat_number=tp.vat_number,
                        siret=tp.siret,
                        ape_code=tp.ape_code,
                    )
                except Exception as exc:
                    logger.warning(
                        "sync_boond_update_company_failed",
                        cr_id=str(cr.id),
                        error=str(exc),
                    )

        if tp and not tp.boond_provider_id:
            try:
                provider_id = await self._crm.create_company_full(
                    company_name=tp.company_name or "",
                    state=9,
                    postcode=tp.head_office_postal_code,
                    address=tp.head_office_street or tp.head_office_address,
                    town=tp.head_office_city,
                    country="France",
                    vat_number=tp.vat_number,
                    siret=tp.siret,
                    legal_status=legal_status,
                    registered_office=registered_office,
                    ape_code=tp.ape_code or "6202A",
                    agency_id=company.boond_agency_id if company else None,
                )
                tp.boond_provider_id = provider_id
                await self._tp_repo.save(tp)
                company_created_now = True
                logger.info(
                    "sync_boond_company_created",
                    cr_id=str(cr.id),
                    provider_id=provider_id,
                )
            except Exception as exc:
                logger.warning(
                    "sync_boond_create_company_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

        # ── Étape 1b : Coordonnées bancaires (IBAN/BIC) ─────────────────────
        # Push bank details from the RIB document to the Boond company via SEPA app.
        if tp and tp.boond_provider_id:
            try:
                from app.vigilance.infrastructure.adapters.postgres_document_repo import (
                    DocumentRepository as _DocRepo,
                )

                doc_repo = _DocRepo(self._db)
                rib_docs = await doc_repo.list_by_third_party(tp.id)
                rib_doc = next(
                    (
                        d
                        for d in rib_docs
                        if d.document_type.value == "rib" and d.auto_check_results
                    ),
                    None,
                )
                if rib_doc and rib_doc.auto_check_results:
                    iban = rib_doc.auto_check_results.get("iban")
                    bic = rib_doc.auto_check_results.get("bic")
                    beneficiaire = rib_doc.auto_check_results.get("beneficiaire", "RIB Fournisseur")
                    if iban and bic:
                        await self._crm.update_company_bank_details(
                            company_id=tp.boond_provider_id,
                            iban=iban,
                            bic=bic,
                            description=beneficiaire or "RIB Fournisseur",
                        )
                        logger.info(
                            "sync_boond_bank_details_pushed",
                            cr_id=str(cr.id),
                            company_id=tp.boond_provider_id,
                        )
                    else:
                        logger.info(
                            "sync_boond_bank_details_skipped_missing_data",
                            cr_id=str(cr.id),
                            has_iban=bool(iban),
                            has_bic=bool(bic),
                        )
                else:
                    logger.info(
                        "sync_boond_bank_details_skipped_no_rib",
                        cr_id=str(cr.id),
                    )
            except Exception as exc:
                logger.warning(
                    "sync_boond_bank_details_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

        # ── Étape 2 : Création des contacts (dédupliqués) ─────────────────
        # Contacts du fournisseur : rôles, types Boond et dédoublonnage sont
        # dans `boond_contacts`, partagés avec l'action manuelle de l'ADV.
        boond_contact_ids: dict[str, int] = {}

        if tp and tp.boond_provider_id:
            # Idempotence : réutiliser les contacts déjà créés lors d'un run
            # précédent — un retry-boond-sync ne doit pas créer de doublons.
            for role, contact_id in persisted_contact_ids(tp).items():
                if contact_id:
                    boond_contact_ids[role] = contact_id

            agency_id = company.boond_agency_id if company else None
            to_create, _already_pushed = split_supplier_contacts(tp)
            for contact in to_create:
                # Société déjà dans le CRM : un contact qu'elle connaît est
                # repris plutôt que doublé.
                if not company_created_now:
                    existing_id = await find_existing_contact_id(
                        self._crm, tp.boond_provider_id, contact
                    )
                    if existing_id:
                        for role in contact.roles:
                            boond_contact_ids[role] = existing_id
                        continue
                try:
                    contact_id = await self._crm.create_contact(
                        company_id=tp.boond_provider_id,
                        civility=contact.civility,
                        first_name=contact.first_name,
                        last_name=contact.last_name,
                        email=contact.email,
                        phone=contact.phone,
                        job_title=contact.job_title,
                        types_of=list(contact.types_of),
                        postcode=tp.head_office_postal_code,
                        address=tp.head_office_street or tp.head_office_address,
                        town=tp.head_office_city,
                        agency_id=agency_id,
                    )
                    for role in contact.roles:
                        boond_contact_ids[role] = contact_id
                except Exception as exc:
                    logger.warning(
                        "sync_boond_create_contact_failed",
                        cr_id=str(cr.id),
                        types_of=list(contact.types_of),
                        error=str(exc),
                    )

            # Persist contact IDs on ThirdParty
            if boond_contact_ids.get("signataire"):
                tp.boond_signatory_contact_id = boond_contact_ids["signataire"]
            if boond_contact_ids.get("adv"):
                tp.boond_adv_contact_id = boond_contact_ids["adv"]
            if boond_contact_ids.get("facturation"):
                tp.boond_billing_contact_id = boond_contact_ids["facturation"]
            if boond_contact_ids:
                await self._tp_repo.save(tp)

        # ── Étape 3 : Conversion candidat → ressource ──────────────────────
        # N'effectuer la conversion que si le consultant est un candidat Boond.
        # If already a resource (boond_consultant_type == "resource"), skip.
        # Boond exige la relation dependsOn (manager) lors de la conversion.
        manager_id: int | None = None
        if cr.boond_need_id:
            try:
                need_data = await self._crm.get_need(cr.boond_need_id)
                if need_data:
                    manager_id = need_data.get("manager_id")
            except Exception as exc:
                logger.warning(
                    "sync_boond_get_need_for_manager_failed",
                    cr_id=str(cr.id),
                    need_id=cr.boond_need_id,
                    error=str(exc),
                )

        # Fallback: get manager from candidate info (dependsOn relationship)
        if not manager_id and resource_id:
            try:
                candidate_info = await self._crm.get_candidate_info(
                    resource_id,
                    cr.boond_consultant_type,
                )
                if candidate_info and candidate_info.get("manager_id"):
                    manager_id = candidate_info["manager_id"]
            except Exception:
                pass  # Best effort

        is_candidate = cr.boond_consultant_type == "candidate" or cr.boond_consultant_type is None
        is_resource = not is_candidate  # Already a resource in Boond
        if resource_id and is_candidate:
            try:
                new_resource_id = await self._crm.convert_candidate_to_resource(
                    resource_id,
                    state=3,
                    state_reason_type_of=state_reason_type_of(cr.third_party_type),
                    # Le type de ressource distingue le portage commercial des
                    # autres externes ; le motif, lui, ne connaît qu'interne ou
                    # externe.
                    type_of=resource_type_of(cr.third_party_type),
                    manager_id=manager_id,
                )
                is_resource = True
                # Update resource_id if Boond assigned a new ID after conversion
                if new_resource_id and new_resource_id != resource_id:
                    logger.info(
                        "sync_boond_resource_id_changed",
                        cr_id=str(cr.id),
                        old_id=resource_id,
                        new_id=new_resource_id,
                    )
                    resource_id = new_resource_id
                    cr.boond_candidate_id = new_resource_id
                cr.boond_consultant_type = "resource"
                # Store resource ID on ThirdParty for document uploads
                if tp and resource_id:
                    tp.boond_resource_id = resource_id
            except Exception as exc:
                logger.warning(
                    "sync_boond_convert_candidate_failed",
                    cr_id=str(cr.id),
                    resource_id=resource_id,
                    consultant_type=cr.boond_consultant_type,
                    error=str(exc),
                )
        elif resource_id and cr.boond_consultant_type == "resource":
            logger.info(
                "sync_boond_skip_convert_already_resource",
                cr_id=str(cr.id),
                resource_id=resource_id,
            )
            # Resolve actual resource ID from Boond candidate relationships
            try:
                resolved = await self._crm.resolve_resource_id(resource_id)
                if resolved and resolved != resource_id:
                    logger.info(
                        "sync_boond_resolved_resource_id",
                        cr_id=str(cr.id),
                        candidate_id=resource_id,
                        resolved_resource_id=resolved,
                    )
                    resource_id = resolved
                    cr.boond_resource_id = resolved
            except Exception:
                pass  # Best effort
            if tp and resource_id:
                tp.boond_resource_id = resource_id

        # ── Étape 4a : Lien fournisseur → ressource (administrative) ───────
        # Link the resource to the provider company and commercial contact.
        # This is independent of having a daily_rate (contrat cadre workflow).
        # We attempt this even if conversion failed — the person may already
        # be a resource in Boond (trigger ressource_4/5) or become one later.
        is_external = cr.third_party_type != "salarie"
        if resource_id and is_external and tp and tp.boond_provider_id:
            # Contact rattaché à la ressource côté Boond : celui de la
            # facturation, seul contact fournisseur que porte l'onglet
            # administratif.
            provider_contact_id = tp.boond_billing_contact_id or boond_contact_ids.get(
                "facturation"
            )
            logger.info(
                "sync_boond_link_provider_to_resource",
                cr_id=str(cr.id),
                resource_id=resource_id,
                provider_company_id=tp.boond_provider_id,
                provider_contact_id=provider_contact_id,
                tp_boond_billing_contact_id=tp.boond_billing_contact_id,
                boond_contact_ids=boond_contact_ids,
            )
            try:
                await self._crm.update_resource_administrative(
                    resource_id=resource_id,
                    provider_company_id=tp.boond_provider_id,
                    provider_contact_id=provider_contact_id,
                )
            except Exception as exc:
                logger.warning(
                    "sync_boond_update_resource_admin_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

        # Persist resource_id on ThirdParty (always use the resolved local variable)
        if tp and resource_id:
            tp.boond_resource_id = resource_id
            await self._tp_repo.save(tp)

        # ── Étape 6 : Transition → ACTIVE ─────────────────────────────────
        if cr.status == ContractRequestStatus.SIGNED:
            cr.transition_to(ContractRequestStatus.ACTIVE)
        saved = await self._cr_repo.save(cr)

        logger.info(
            "sync_boond_after_signing_complete",
            cr_id=str(saved.id),
            reference=cr.display_reference,
        )
        return saved

    async def _get_contract_company(self, company_id):
        """Fetch the ContractCompanyModel for the given ID or the default."""
        from app.contract_management.infrastructure.models import ContractCompanyModel

        if company_id:
            result = await self._db.execute(
                select(ContractCompanyModel).where(ContractCompanyModel.id == company_id)
            )
            return result.scalar_one_or_none()

        result = await self._db.execute(
            select(ContractCompanyModel)
            .where(ContractCompanyModel.is_default.is_(True))
            .where(ContractCompanyModel.is_active.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none()
