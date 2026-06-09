"""Use case: Generate dynamic charter documents (AR + engagement) for a consultant."""

import base64
from datetime import datetime
from pathlib import Path
from uuid import UUID

import structlog

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "templates"


class GenerateCharterDocumentsUseCase:
    """Generate PDF documents for consultant charter signing.

    Produces:
    1. Accusé de réception charte informatique (AR)
    2. Engagement de confidentialité

    Both are HTML templates rendered to PDF via WeasyPrint,
    with dynamic consultant and company data.
    """

    def __init__(
        self,
        contract_request_repository,
        s3_service,
        db=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._s3 = s3_service
        self._db = db

    async def execute(
        self,
        contract_request_id: UUID,
        consultant_first_name: str,
        consultant_last_name: str,
        consultant_email: str,
        consultant_civility: str = "",
        consultant_phone: str = "",
        charter_version: str = "V1",
    ) -> dict[str, str]:
        """Generate charter PDFs and upload to S3.

        Returns:
            Dict with s3 keys: {"ar_s3_key": ..., "engagement_s3_key": ...}
        """

        cr = await self._cr_repo.get_by_id(contract_request_id)
        if not cr:
            raise ValueError(f"Contract request {contract_request_id} not found")

        # Load company info
        company = await self._load_company(cr)
        logo_b64, logo_mime = None, None
        if company and getattr(company, "logo_s3_key", None):
            try:
                content = await self._s3.download_file(company.logo_s3_key)
                logo_b64 = base64.b64encode(content).decode()
                ext = company.logo_s3_key.rsplit(".", 1)[-1].lower()
                mime_map = {"png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml"}
                logo_mime = mime_map.get(ext, "image/png")
            except Exception:
                pass

        # Build template context
        context = {
            "consultant_civility": consultant_civility or "",
            "consultant_first_name": consultant_first_name,
            "consultant_last_name": consultant_last_name,
            "consultant_email": consultant_email,
            "consultant_phone": consultant_phone or "",
            "charter_version": charter_version,
            "date": datetime.utcnow().strftime("%d/%m/%Y"),
            "issuer_company_name": company.name if company else "Bobby",
            "issuer_legal_form": company.legal_form if company else "",
            "issuer_capital": company.capital if company else "",
            "issuer_head_office": company.head_office if company else "",
            "issuer_rcs_city": company.rcs_city if company else "",
            "issuer_rcs_number": company.rcs_number if company else "",
            "issuer_color_code": company.color_code if company else "#4BBEA8",
            "logo_b64": logo_b64,
            "logo_mime": logo_mime,
        }

        ref = cr.display_reference
        results = {}

        # Generate AR charte informatique
        ar_html = self._render_template("ar_charte_informatique.html", context)
        ar_pdf = await self._html_to_pdf(ar_html)
        ar_key = f"charters/consultants/{ref}/AR_charte_informatique_{consultant_last_name}.pdf"
        await self._s3.upload_file(key=ar_key, content=ar_pdf, content_type="application/pdf")
        results["ar_s3_key"] = ar_key

        # Generate engagement de confidentialité
        eng_html = self._render_template("engagement_confidentialite.html", context)
        eng_pdf = await self._html_to_pdf(eng_html)
        eng_key = (
            f"charters/consultants/{ref}/Engagement_confidentialite_{consultant_last_name}.pdf"
        )
        await self._s3.upload_file(key=eng_key, content=eng_pdf, content_type="application/pdf")
        results["engagement_s3_key"] = eng_key

        logger.info(
            "charter_documents_generated",
            cr_id=str(contract_request_id),
            consultant=f"{consultant_first_name} {consultant_last_name}",
            keys=results,
        )
        return results

    @staticmethod
    def _render_template(template_name: str, context: dict) -> str:
        """Render a Jinja2 HTML template."""
        from jinja2 import Template

        template_path = TEMPLATES_DIR / template_name
        with open(template_path, encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**context)

    @staticmethod
    async def _html_to_pdf(html_content: str) -> bytes:
        """Convert HTML to PDF using WeasyPrint."""
        import asyncio

        from weasyprint import HTML

        def _generate():
            return HTML(string=html_content).write_pdf()

        return await asyncio.to_thread(_generate)

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
