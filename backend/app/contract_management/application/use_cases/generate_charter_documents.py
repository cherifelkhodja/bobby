"""Use case: Generate the charter documents (chartes, AR, engagement) as PDFs."""

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog

from app.contract_management.infrastructure.adapters.pdf_rendering import render_pdf

logger = structlog.get_logger()

# Version de la charte servie par défaut, reprise des maquettes.
DEFAULT_CHARTER_VERSION = "2026.1"


@dataclass(frozen=True)
class CharterDocument:
    """One generated document: which template, for whom, and how it is named."""

    key: str
    template: str
    target: str  # consultant | partner
    file_stem: str
    result_key: str


# Les documents des maquettes Claude Design, groupés par destinataire.
# `result_key` est la clé renvoyée par `execute()` ; `ar_s3_key` et
# `engagement_s3_key` sont conservées telles quelles, l'API les expose déjà.
CHARTER_DOCUMENTS: tuple[CharterDocument, ...] = (
    CharterDocument(
        key="charte_informatique",
        template="charte_informatique.html",
        target="consultant",
        file_stem="Charte_informatique",
        result_key="charte_informatique_s3_key",
    ),
    CharterDocument(
        key="ar_charte_informatique",
        template="ar_charte_informatique.html",
        target="consultant",
        file_stem="AR_charte_informatique",
        result_key="ar_s3_key",
    ),
    CharterDocument(
        key="engagement_confidentialite",
        template="engagement_confidentialite.html",
        target="consultant",
        file_stem="Engagement_confidentialite",
        result_key="engagement_s3_key",
    ),
    CharterDocument(
        key="charte_achats_responsables",
        template="charte_achats_responsables.html",
        target="partner",
        file_stem="Charte_achats_responsables",
        result_key="charte_achats_responsables_s3_key",
    ),
    CharterDocument(
        key="ar_charte_achats_responsables",
        template="ar_charte_achats_responsables.html",
        target="partner",
        file_stem="AR_charte_achats_responsables",
        result_key="ar_achats_responsables_s3_key",
    ),
)


def documents_for(target: str) -> tuple[CharterDocument, ...]:
    """Return the documents to generate for a target (``consultant``/``partner``)."""
    return tuple(doc for doc in CHARTER_DOCUMENTS if doc.target == target)


class GenerateCharterDocumentsUseCase:
    """Generate the charter PDFs for a contract request and upload them to S3.

    Consultant set — charte informatique, its acknowledgement, and the
    confidentiality undertaking. Partner set — charte des achats responsables
    and its acknowledgement.

    Every document is an HTML Jinja2 template rendered by WeasyPrint, branded
    with the issuing company's palette.
    """

    def __init__(
        self,
        contract_request_repository,
        s3_service,
        db=None,
        third_party_repository=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._s3 = s3_service
        self._db = db
        self._tp_repo = third_party_repository

    async def execute(
        self,
        contract_request_id: UUID,
        consultant_first_name: str = "",
        consultant_last_name: str = "",
        consultant_email: str = "",
        consultant_civility: str = "",
        consultant_phone: str = "",
        charter_version: str = DEFAULT_CHARTER_VERSION,
        target: str = "consultant",
    ) -> dict[str, str]:
        """Generate the documents for ``target`` and upload them to S3.

        Returns:
            Mapping of each document's ``result_key`` to its S3 key.
        """
        documents = documents_for(target)
        if not documents:
            raise ValueError(f"Destinataire de charte inconnu : {target}")

        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ValueError(f"Contract request {contract_request_id} not found")

        company = await self._load_company(cr)
        context = self._build_context(
            cr=cr,
            company=company,
            logo=await self._load_logo(company),
            consultant_civility=consultant_civility,
            consultant_first_name=consultant_first_name,
            consultant_last_name=consultant_last_name,
            consultant_email=consultant_email,
            consultant_phone=consultant_phone,
            charter_version=charter_version,
        )
        if target == "partner":
            context.update(await self._partner_context(cr))

        # Nom de fichier : le consultant pour ses documents, le tiers pour ceux
        # du partenaire — les deux jeux cohabitent sous la même référence.
        if target == "partner":
            subject = context.get("partner_company_name") or "partenaire"
        else:
            subject = consultant_last_name or "consultant"
        slug = _slugify(subject)

        results: dict[str, str] = {}
        for document in documents:
            pdf = await asyncio.to_thread(render_pdf, document.template, dict(context))
            s3_key = f"charters/{target}s/{cr.display_reference}/{document.file_stem}_{slug}.pdf"
            await self._s3.upload_file(key=s3_key, content=pdf, content_type="application/pdf")
            results[document.result_key] = s3_key

        logger.info(
            "charter_documents_generated",
            cr_id=str(contract_request_id),
            target=target,
            subject=subject,
            keys=results,
        )
        return results

    @staticmethod
    def _build_context(
        *,
        cr,
        company,
        logo: tuple[str, str] | None,
        consultant_civility: str,
        consultant_first_name: str,
        consultant_last_name: str,
        consultant_email: str,
        consultant_phone: str,
        charter_version: str,
    ) -> dict:
        """Build the template context shared by every charter document."""
        logo_b64, logo_mime = logo if logo else (None, None)
        return {
            "consultant_civility": consultant_civility or "",
            "consultant_first_name": consultant_first_name or "",
            "consultant_last_name": consultant_last_name or "",
            "consultant_email": consultant_email or "",
            "consultant_phone": consultant_phone or "",
            "charter_version": charter_version,
            "date": datetime.utcnow().strftime("%d/%m/%Y"),
            "reference": cr.display_reference,
            "mission_title": getattr(cr, "mission_title", "") or "",
            "client_name": getattr(cr, "client_name", "") or "",
            # Société émettrice
            "issuer_company_name": company.name if company else "Bobby",
            "issuer_legal_form": company.legal_form if company else "",
            "issuer_capital": company.capital if company else "",
            "issuer_head_office": company.head_office if company else "",
            "issuer_rcs_city": company.rcs_city if company else "",
            "issuer_rcs_number": company.rcs_number if company else "",
            "issuer_representative_is_entity": (
                company.representative_is_entity if company else False
            ),
            "issuer_representative_name": company.representative_name if company else "",
            "issuer_representative_quality": company.representative_quality if company else "",
            "issuer_representative_sub_quality": (
                getattr(company, "representative_sub_quality", "") or "" if company else ""
            ),
            "issuer_signatory_name": company.signatory_name if company else "",
            "issuer_tva_number": (getattr(company, "tva_number", "") or "") if company else "",
            "issuer_color_code": company.color_code if company else "#4BBEA8",
            "ethics_alert_email": _ethics_alert_email(company),
            "logo_b64": logo_b64,
            "logo_mime": logo_mime,
        }

    async def _partner_context(self, cr) -> dict:
        """Third-party identity used by the partner acknowledgement."""
        if not (self._tp_repo and cr.third_party_id):
            return {}
        tp = await self._tp_repo.get_by_id(cr.third_party_id)
        if not tp:
            return {}
        return {
            "partner_company_name": tp.company_name or "",
            "partner_representative_civility": tp.representative_civility or "",
            "partner_representative_name": tp.representative_name or "",
            "partner_representative_title": tp.representative_title or "",
        }

    async def _load_logo(self, company) -> tuple[str, str] | None:
        """Download the company logo from S3 as (base64, mime), or None."""
        if not company or not getattr(company, "logo_s3_key", None):
            return None
        try:
            content = await self._s3.download_file(company.logo_s3_key)
        except Exception:
            logger.warning("charter_logo_load_failed", s3_key=company.logo_s3_key)
            return None
        ext = company.logo_s3_key.rsplit(".", 1)[-1].lower()
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "svg": "image/svg+xml",
            "webp": "image/webp",
        }
        return base64.b64encode(content).decode(), mime_map.get(ext, "image/png")

    async def _load_company(self, cr):
        """Load the issuing company."""
        if not self._db:
            return None
        from sqlalchemy import select

        from app.contract_management.infrastructure.models import ContractCompanyModel

        company_id = cr.company_id
        if not company_id:
            result = await self._db.execute(
                select(ContractCompanyModel)
                .where(ContractCompanyModel.is_default.is_(True))
                .where(ContractCompanyModel.is_active.is_(True))
            )
            return result.scalar_one_or_none()
        result = await self._db.execute(
            select(ContractCompanyModel).where(ContractCompanyModel.id == company_id)
        )
        return result.scalar_one_or_none()


def _ethics_alert_email(company) -> str:
    """Ethics-alert address quoted by the charte des achats responsables.

    Derived from the company's sender address so a newly created company gets a
    plausible one; the section is omitted when nothing can be derived.
    """
    sender = getattr(company, "email_from", None) if company else None
    if not sender or "@" not in sender:
        return ""
    return f"alerte-ethique@{sender.rsplit('@', 1)[1]}"


def _slugify(value: str) -> str:
    """Reduce a name to a filename-safe token."""
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_only).strip("_") or "document"
