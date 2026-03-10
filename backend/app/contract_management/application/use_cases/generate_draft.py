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
    """Generate a contract draft PDF and upload to S3.

    Verifies compliance (soft block unless overridden), generates
    the PDF using the HTML template, uploads to S3, and creates
    a Contract entity.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        contract_generator,
        article_template_repository,
        s3_service,
        settings,
        db=None,
        annex_template_repository=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._generator = contract_generator
        self._article_repo = article_template_repository
        self._annex_repo = annex_template_repository
        self._s3 = s3_service
        self._settings = settings
        self._db = db  # AsyncSession for loading company

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
        articles = await self._article_repo.get_active()
        annexes = await self._annex_repo.get_active() if self._annex_repo else []
        company = await self._load_company(cr)
        logo_result = await self._load_company_logo(company)
        template_context = self._build_context(cr, tp, articles, company, annexes)
        if logo_result:
            logo_b64, logo_mime = logo_result
            template_context["logo_b64"] = logo_b64
            template_context["logo_mime"] = logo_mime

        # Generate PDF
        pdf_content = await self._generator.generate_draft(template_context)

        # Determine version number (increment if regenerating)
        existing_contract = await self._contract_repo.get_by_request_id(cr.id)
        new_version = (existing_contract.version + 1) if existing_contract else 1

        # Upload to S3 with versioned key
        s3_key = f"contracts/{cr.display_reference}/draft_v{new_version}.pdf"
        await self._s3.upload_file(
            key=s3_key,
            content=pdf_content,
            content_type="application/pdf",
        )

        # Always create a new contract record for the new version
        contract = Contract(
            contract_request_id=cr.id,
            third_party_id=cr.third_party_id or cr.id,
            reference=cr.display_reference,
            s3_key_draft=s3_key,
            version=new_version,
        )
        saved_contract = await self._contract_repo.save(contract)

        # Transition CR status (self-transition allowed when already draft_generated)
        cr.transition_to(ContractRequestStatus.DRAFT_GENERATED)
        await self._cr_repo.save(cr)

        logger.info(
            "contract_draft_generated",
            cr_id=str(cr.id),
            contract_id=str(saved_contract.id),
            s3_key=s3_key,
        )
        return saved_contract

    async def _load_company(self, cr):
        """Load the issuing company from DB, or return None to use settings fallback."""
        if not self._db:
            return None
        company_id = None
        if cr.contract_config and isinstance(cr.contract_config, dict):
            raw = cr.contract_config.get("company_id")
            if raw:
                from uuid import UUID as _UUID
                try:
                    company_id = _UUID(str(raw))
                except (ValueError, AttributeError):
                    pass
        if not company_id:
            # Fall back to default company
            from sqlalchemy import select as _select
            from app.contract_management.infrastructure.models import ContractCompanyModel
            result = await self._db.execute(
                _select(ContractCompanyModel)
                .where(ContractCompanyModel.is_default.is_(True))
                .where(ContractCompanyModel.is_active.is_(True))
            )
            return result.scalar_one_or_none()
        from sqlalchemy import select as _select
        from app.contract_management.infrastructure.models import ContractCompanyModel
        result = await self._db.execute(
            _select(ContractCompanyModel).where(ContractCompanyModel.id == company_id)
        )
        return result.scalar_one_or_none()

    async def _load_company_logo(self, company) -> tuple[str, str] | None:
        """Download company logo from S3 and return (base64, mime_type), or None."""
        if not company or not getattr(company, "logo_s3_key", None):
            return None
        try:
            import base64 as _b64
            content = await self._s3.download_file(company.logo_s3_key)
            ext = company.logo_s3_key.rsplit(".", 1)[-1].lower() if "." in company.logo_s3_key else "png"
            mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml", "webp": "image/webp"}
            mime = mime_map.get(ext, "image/png")
            return _b64.b64encode(content).decode(), mime
        except Exception:
            logger.warning("company_logo_load_failed", s3_key=company.logo_s3_key)
            return None

    def _build_context(self, cr, tp, articles: list, company=None, annexes: list | None = None) -> dict:
        """Build template context from contract request and third party."""
        # ── Issuing company info (from DB or settings fallback) ──
        if company:
            issuer_company_name = company.name
            issuer_legal_form = company.legal_form
            issuer_capital = company.capital
            issuer_head_office = company.head_office
            issuer_rcs_city = company.rcs_city
            issuer_rcs_number = company.rcs_number
            issuer_representative_is_entity = company.representative_is_entity
            issuer_representative_name = company.representative_name
            issuer_representative_quality = company.representative_quality
            issuer_representative_sub_name = company.representative_sub_name or ""
            issuer_representative_sub_quality = company.representative_sub_quality or ""
            issuer_signatory_name = company.signatory_name
            issuer_color_code = company.color_code
            invoices_company_mail = company.invoices_company_mail or ""
        else:
            # Legacy fallback: use settings
            issuer_company_name = self._settings.GEMINI_COMPANY_NAME_CONTRACT
            issuer_legal_form = self._settings.GEMINI_LEGAL_FORM
            issuer_capital = self._settings.GEMINI_CAPITAL
            issuer_head_office = self._settings.GEMINI_HEAD_OFFICE
            issuer_rcs_city = self._settings.GEMINI_RCS_CITY
            issuer_rcs_number = self._settings.GEMINI_RCS_NUMBER
            # Settings use the old "entity" style by default
            issuer_representative_is_entity = True
            issuer_representative_name = self._settings.GEMINI_REPRESENTATIVE_ENTITY
            issuer_representative_quality = self._settings.GEMINI_REPRESENTATIVE_QUALITY
            issuer_representative_sub_name = self._settings.GEMINI_REPRESENTATIVE_SUB
            issuer_representative_sub_quality = ""
            issuer_signatory_name = self._settings.GEMINI_SIGNATORY_NAME
            issuer_color_code = "#4BBEA8"
            invoices_company_mail = ""

        context = {
            # Issuing company (new unified variables)
            "issuer_company_name": issuer_company_name,
            "issuer_legal_form": issuer_legal_form,
            "issuer_capital": issuer_capital,
            "issuer_head_office": issuer_head_office,
            "issuer_rcs_city": issuer_rcs_city,
            "issuer_rcs_number": issuer_rcs_number,
            "issuer_representative_is_entity": issuer_representative_is_entity,
            "issuer_representative_name": issuer_representative_name,
            "issuer_representative_quality": issuer_representative_quality,
            "issuer_representative_sub_name": issuer_representative_sub_name,
            "issuer_representative_sub_quality": issuer_representative_sub_quality,
            "issuer_signatory_name": issuer_signatory_name,
            "issuer_color_code": issuer_color_code,
            "invoices_company_mail": invoices_company_mail,
            # Keep legacy aliases so existing article templates still work
            "gemini_company_name": issuer_company_name,
            "gemini_legal_form": issuer_legal_form,
            "gemini_capital": issuer_capital,
            "gemini_head_office": issuer_head_office,
            "gemini_rcs_city": issuer_rcs_city,
            "gemini_rcs_number": issuer_rcs_number,
            "gemini_signatory_name": issuer_signatory_name,
            # Contract details
            "reference": cr.display_reference,
            "daily_rate": str(cr.daily_rate) if cr.daily_rate else "",
            "start_date": cr.start_date.strftime("%d/%m/%Y") if cr.start_date else "",
            "client_name": cr.client_name or "",
            "mission_description": cr.mission_description or "",
            "mission_site_name": cr.mission_site_name or "",
            "mission_address": cr.mission_address or "",
            "mission_postal_code": cr.mission_postal_code or "",
            "mission_city": cr.mission_city or "",
            "consultant_civility": cr.consultant_civility or "",
            "consultant_first_name": cr.consultant_first_name or "",
            "consultant_last_name": cr.consultant_last_name or "",
            "consultant_email": cr.consultant_email or "",
            "consultant_phone": cr.consultant_phone or "",
        }

        # Partner info
        if tp:
            context.update(
                {
                    "partner_company_name": tp.company_name,
                    "partner_legal_form": tp.legal_form,
                    "partner_capital": tp.capital or "",
                    "partner_head_office": tp.head_office_address,
                    "partner_rcs_city": tp.rcs_city,
                    "partner_rcs_number": tp.rcs_number or tp.siren,
                    "partner_representative_name": tp.representative_name,
                    "partner_representative_title": tp.representative_title,
                    "partner_siren": tp.siren,
                    "partner_siret": tp.siret,
                    # Correspondant partenaire (contact ADV du tiers)
                    "contact_first_name": getattr(tp, "adv_contact_first_name", None) or "",
                    "contact_last_name": getattr(tp, "adv_contact_last_name", None) or "",
                    "contact_email": (
                        getattr(tp, "adv_contact_email", None)
                        or getattr(tp, "contact_email", None)
                        or ""
                    ),
                }
            )

        # Correspondant commercial (main manager côté émetteur)
        context.update(
            {
                "main_manager_first_name": "",  # surchargé via contract_config si disponible
                "main_manager_last_name": "",
                "main_manager_email": cr.commercial_email or "",
                # agency_name = nom de la société émettrice (ou override via contract_config)
                "agency_name": issuer_company_name,
                # adv_email : email ADV émetteur (override via contract_config)
                "adv_email": "",
            }
        )

        # Contract config (clauses, including tacit_renewal_months).
        # Merge config first, then re-apply the authoritative cr fields so that
        # None/0 values from a partially-filled config cannot overwrite formatted values.
        if cr.contract_config:
            context.update(cr.contract_config)

        # Re-apply authoritative formatted fields from cr (they take priority over config).
        from datetime import date as _date

        def _fmt_date(d) -> str:
            if d is None:
                return ""
            if isinstance(d, _date):
                return d.strftime("%d/%m/%Y")
            return str(d) if d else ""

        context["start_date"] = _fmt_date(cr.start_date) or _fmt_date(context.get("start_date"))
        context["end_date"] = _fmt_date(cr.end_date) or _fmt_date(context.get("end_date"))
        context["daily_rate"] = str(cr.daily_rate) if cr.daily_rate else ""
        context["mission_title"] = cr.mission_title or ""

        # Convert any remaining None values to empty strings so the template never shows "None".
        for key, value in list(context.items()):
            if value is None:
                context[key] = ""

        # Resolve human-readable display values for payment config
        from app.contract_management.domain.value_objects.payment_terms import (
            InvoiceSubmissionMethod,
            PaymentTerms,
        )

        payment_terms_raw = context.get("payment_terms", "net_30")
        try:
            context["payment_terms_display"] = PaymentTerms(payment_terms_raw).display_text
        except ValueError:
            context["payment_terms_display"] = payment_terms_raw

        invoice_method_raw = context.get("invoice_submission_method", "email")
        _issuer = context.get("issuer_company_name", "")
        _mail = context.get("invoices_company_mail", "")
        _invoice_display_map = {
            "boondmanager": f"Les factures seront à déposer sur la plateforme Boondmanager de la société {_issuer}",
            "email": f"Les factures seront à envoyer exclusivement à l'adresse suivante {_mail}",
        }
        context["invoice_submission_method_display"] = _invoice_display_map.get(
            invoice_method_raw, invoice_method_raw
        )

        # Pre-render each article's content as a Jinja2 template so that
        # article authors can embed variables (e.g. {{ payment_terms_display }})
        from dataclasses import replace as dc_replace

        from jinja2 import BaseLoader, Environment

        jinja_env = Environment(loader=BaseLoader(), autoescape=False)

        # Filter out optional articles that were excluded for this contract
        excluded_keys: list[str] = []
        deleted_article_keys: list[str] = []
        deleted_annex_keys: list[str] = []
        article_overrides: dict[str, str] = {}
        annex_overrides: dict[str, str] = {}
        if cr.contract_config and isinstance(cr.contract_config, dict):
            excluded_keys = cr.contract_config.get("excluded_optional_article_keys", []) or []
            deleted_article_keys = cr.contract_config.get("deleted_article_keys", []) or []
            deleted_annex_keys = cr.contract_config.get("deleted_annex_keys", []) or []
            article_overrides = cr.contract_config.get("article_overrides") or {}
            annex_overrides = cr.contract_config.get("annex_overrides") or {}

        selected_articles = [
            a for a in articles
            if not (a.is_optional and a.article_key in excluded_keys)
            and a.article_key not in deleted_article_keys
        ]

        # Re-number sequentially after filtering
        rendered_articles = []
        counter = 0
        for article in selected_articles:
            if article.article_key != "preambule":
                counter += 1
                article = dc_replace(article, article_number=counter)
            # Per-contract override takes priority over template content
            raw_content = article_overrides.get(article.article_key, article.content)
            try:
                rendered_content = jinja_env.from_string(raw_content).render(**context)
            except Exception:
                rendered_content = raw_content
            rendered_articles.append(dc_replace(article, content=rendered_content))

        context["articles"] = rendered_articles

        # Pre-render active annexes, filtering conditionals based on contract config
        rendered_annexes = []
        for annexe in (annexes or []):
            if annexe.annexe_key in deleted_annex_keys:
                continue
            if annexe.is_conditional and annexe.condition_field:
                field_value = context.get(annexe.condition_field, "")
                if not field_value:
                    continue
            # Per-contract override takes priority over template content
            raw_content = annex_overrides.get(annexe.annexe_key, annexe.content)
            try:
                rendered_content = jinja_env.from_string(raw_content).render(**context)
            except Exception:
                rendered_content = raw_content
            from dataclasses import replace as _dc_replace
            rendered_annexes.append(_dc_replace(annexe, content=rendered_content))

        context["annexes"] = rendered_annexes

        return context
