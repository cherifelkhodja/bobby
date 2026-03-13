"""Use case: Synchronise all data to BoondManager after contract signing."""

import re
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)

logger = structlog.get_logger()

# Maps third_party_type → Boond contract typeOf
_THIRD_PARTY_TYPE_TO_CONTRACT_TYPE: dict[str, int] = {
    "sous_traitant": 2,
    "freelance": 3,
    "portage_salarial": 6,
    "portage_commercial": 7,
}


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
    4. Fetch the resource typeOf to determine if the consultant is external.
    5. If external (typeOf=1): create a Boond contract and update the resource
       administrative data to link it to the provider company/contact.
    6. Create the purchase order.
    7. Transition the contract request to ARCHIVED.
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
            The updated (ARCHIVED) contract request.
        """
        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ValueError(f"Demande de contrat introuvable: {contract_request_id}")

        tp = None
        if cr.third_party_id:
            tp = await self._tp_repo.get_by_id(cr.third_party_id)

        # Fetch the issuing company to get boond_agency_id
        company = await self._get_contract_company(cr.company_id)

        resource_id: int | None = cr.boond_candidate_id

        # ── Étape 1 : Création société fournisseur ─────────────────────────
        # Build formatted legal fields
        legal_status = None
        if tp and tp.legal_form and tp.capital:
            legal_status = f"{tp.legal_form} au capital de {tp.capital} €"
        registered_office = None
        if tp and tp.rcs_number and tp.rcs_city:
            formatted_siren = _format_siren(tp.rcs_number)
            registered_office = f"{formatted_siren} R.C.S. {tp.rcs_city}"

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

        # ── Étape 2 : Création des contacts (dédupliqués) ─────────────────
        # Boond typesOf: 7=dirigeant, 8=commercial, 9=adv, 10=signataire
        boond_contact_ids: dict[str, int] = {}

        if tp and tp.boond_provider_id:
            signatory_types = [10]
            if tp.signatory_is_director:
                signatory_types.append(7)

            role_entries: list[tuple] = [
                (tp.signatory_civility or tp.representative_civility,
                 tp.signatory_first_name or tp.representative_first_name,
                 tp.signatory_last_name or tp.representative_last_name,
                 tp.signatory_email or tp.representative_email,
                 tp.signatory_phone or tp.representative_phone,
                 tp.representative_title, signatory_types, "signataire"),
                (tp.adv_contact_civility, tp.adv_contact_first_name,
                 tp.adv_contact_last_name, tp.adv_contact_email,
                 tp.adv_contact_phone, "ADV", [9], "adv"),
                (tp.billing_contact_civility, tp.billing_contact_first_name,
                 tp.billing_contact_last_name, tp.billing_contact_email,
                 tp.billing_contact_phone, "Commercial", [8], "commercial"),
            ]

            # Merge contacts with same identity
            merged: dict[str, dict] = {}
            for civ, fn, ln, email, phone, job_title, types_of_list, label in role_entries:
                if not (fn or email):
                    continue
                key = f"{(fn or '').strip().lower()}|{(ln or '').strip().lower()}|{(email or '').strip().lower()}"
                if key in merged:
                    merged[key]["types_of"].extend(types_of_list)
                    merged[key]["labels"].append(label)
                    if job_title and job_title not in ("ADV", "Commercial"):
                        merged[key]["job_title"] = job_title
                else:
                    merged[key] = {
                        "civility": civ, "first_name": fn, "last_name": ln,
                        "email": email, "phone": phone, "job_title": job_title,
                        "types_of": list(types_of_list), "labels": [label],
                    }

            agency_id = company.boond_agency_id if company else None
            for entry in merged.values():
                try:
                    contact_id = await self._crm.create_contact(
                        company_id=tp.boond_provider_id,
                        civility=entry["civility"],
                        first_name=entry["first_name"],
                        last_name=entry["last_name"],
                        email=entry["email"],
                        phone=entry["phone"],
                        job_title=entry["job_title"],
                        types_of=entry["types_of"],
                        postcode=tp.head_office_postal_code,
                        address=tp.head_office_street or tp.head_office_address,
                        town=tp.head_office_city,
                        agency_id=agency_id,
                    )
                    for lbl in entry["labels"]:
                        boond_contact_ids[lbl] = contact_id
                except Exception as exc:
                    logger.warning(
                        "sync_boond_create_contact_failed",
                        cr_id=str(cr.id),
                        types_of=entry["types_of"],
                        error=str(exc),
                    )

            # Persist contact IDs on ThirdParty
            if boond_contact_ids.get("signataire"):
                tp.boond_signatory_contact_id = boond_contact_ids["signataire"]
            if boond_contact_ids.get("adv"):
                tp.boond_adv_contact_id = boond_contact_ids["adv"]
            if boond_contact_ids.get("commercial"):
                tp.boond_commercial_contact_id = boond_contact_ids["commercial"]
            if boond_contact_ids:
                await self._tp_repo.save(tp)

        # ── Étape 3 : Conversion candidat → ressource ──────────────────────
        # N'effectuer la conversion que si le consultant est un candidat Boond.
        # Si c'est déjà une ressource (boond_consultant_type == "resource"),
        # l'appel /candidates/{id} échouerait et la conversion est inutile.
        is_candidate = cr.boond_consultant_type == "candidate" or cr.boond_consultant_type is None
        state_reason_type_of = 0 if cr.third_party_type == "salarie" else 1
        if resource_id and is_candidate:
            try:
                await self._crm.convert_candidate_to_resource(
                    resource_id,
                    state=3,
                    state_reason_type_of=state_reason_type_of,
                )
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

        # ── Étape 4 : Vérification typeOf de la ressource ─────────────────
        resource_type_of: int | None = None
        if resource_id:
            resource_type_of = await self._crm.get_resource_type_of(resource_id)
            logger.info(
                "sync_boond_resource_type_of",
                cr_id=str(cr.id),
                resource_id=resource_id,
                type_of=resource_type_of,
            )

        # ── Étape 5 : Contrat + lien administratif (externe uniquement) ───
        if resource_id and resource_type_of == 1 and cr.daily_rate:
            contract_type_of = _THIRD_PARTY_TYPE_TO_CONTRACT_TYPE.get(
                cr.third_party_type or "", 3
            )
            start_date_str = None
            if cr.start_date:
                start_date_str = (
                    cr.start_date.strftime("%Y-%m-%d")
                    if hasattr(cr.start_date, "strftime")
                    else str(cr.start_date)
                )
            agency_id = company.boond_agency_id if company else None

            try:
                await self._crm.create_boond_contract(
                    resource_id=resource_id,
                    positioning_id=cr.boond_positioning_id,
                    daily_rate=float(cr.daily_rate),
                    type_of=contract_type_of,
                    start_date=start_date_str,
                    agency_id=agency_id,
                )
            except Exception as exc:
                logger.warning(
                    "sync_boond_create_contract_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

            if tp and tp.boond_provider_id:
                commercial_contact_id = tp.boond_commercial_contact_id or boond_contact_ids.get("commercial")
                try:
                    await self._crm.update_resource_administrative(
                        resource_id=resource_id,
                        provider_company_id=tp.boond_provider_id,
                        provider_contact_id=commercial_contact_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "sync_boond_update_resource_admin_failed",
                        cr_id=str(cr.id),
                        error=str(exc),
                    )

        # ── Étape 6 : Bon de commande ──────────────────────────────────────
        contract = await self._contract_repo.get_by_request_id(cr.id)
        if tp and tp.boond_provider_id and cr.daily_rate and contract:
            try:
                po_id = await self._crm.create_purchase_order(
                    provider_id=tp.boond_provider_id,
                    positioning_id=cr.boond_positioning_id,
                    reference=cr.display_reference,
                    amount=float(cr.daily_rate),
                )
                contract.boond_purchase_order_id = po_id
                await self._contract_repo.save(contract)
            except Exception as exc:
                logger.warning(
                    "sync_boond_create_purchase_order_failed",
                    cr_id=str(cr.id),
                    error=str(exc),
                )

        # ── Étape 7 : Transition → ARCHIVED (si pas déjà) ────────────────
        if cr.status != ContractRequestStatus.ARCHIVED:
            cr.transition_to(ContractRequestStatus.ARCHIVED)
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
