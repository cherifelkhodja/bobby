"""Service: Regenerate a contract draft PDF with updated reference.

Used after partner approval to regenerate the draft with the final reference
(XXX-CC-NNN) replacing the provisional reference (PROV-YYYY-NNNN).
"""

import structlog

from app.contract_management.domain.entities.contract import Contract

logger = structlog.get_logger()


class DraftRegenerator:
    """Regenerate the contract draft PDF for an existing contract request.

    Reuses the same GenerateDraftUseCase context-building logic but
    skips compliance checks and status transitions — the CR stays
    in PARTNER_APPROVED and only the PDF/S3 artifact is updated.
    """

    def __init__(
        self,
        contract_request_repository,
        contract_repository,
        third_party_repository,
        contract_generator,
        article_template_repository,
        annex_template_repository,
        s3_service,
        settings,
        db=None,
    ) -> None:
        self._cr_repo = contract_request_repository
        self._contract_repo = contract_repository
        self._tp_repo = third_party_repository
        self._generator = contract_generator
        self._article_repo = article_template_repository
        self._annex_repo = annex_template_repository
        self._s3 = s3_service
        self._settings = settings
        self._db = db

    async def regenerate(self, cr) -> Contract:
        """Regenerate the draft PDF for a contract request.

        Args:
            cr: The contract request (with final reference already set).

        Returns:
            The updated Contract entity.
        """
        from app.contract_management.application.use_cases.generate_draft import (
            GenerateDraftUseCase,
        )

        # Borrow _build_context and _load_company from GenerateDraftUseCase
        generator_uc = GenerateDraftUseCase(
            contract_request_repository=self._cr_repo,
            contract_repository=self._contract_repo,
            third_party_repository=self._tp_repo,
            contract_generator=self._generator,
            article_template_repository=self._article_repo,
            s3_service=self._s3,
            settings=self._settings,
            db=self._db,
            annex_template_repository=self._annex_repo,
        )

        tp = await self._tp_repo.get_by_id(cr.third_party_id) if cr.third_party_id else None
        articles = await self._article_repo.get_active()
        annexes = await self._annex_repo.get_active() if self._annex_repo else []
        company = await generator_uc._load_company(cr)
        logo_result = await generator_uc._load_company_logo(company)
        context = generator_uc._build_context(cr, tp, articles, company, annexes)
        if logo_result:
            logo_b64, logo_mime = logo_result
            context["logo_b64"] = logo_b64
            context["logo_mime"] = logo_mime

        # Generate PDF with final reference
        pdf_content = await self._generator.generate_draft(context)

        # Determine version (increment from existing)
        existing = await self._contract_repo.get_by_request_id(cr.id)
        new_version = (existing.version + 1) if existing else 1

        # Upload to S3
        s3_key = f"contracts/{cr.display_reference}/draft_v{new_version}.pdf"
        await self._s3.upload_file(
            key=s3_key,
            content=pdf_content,
            content_type="application/pdf",
        )

        # Create new contract record with final reference
        contract = Contract(
            contract_request_id=cr.id,
            third_party_id=cr.third_party_id or cr.id,
            reference=cr.display_reference,
            s3_key_draft=s3_key,
            version=new_version,
        )
        saved = await self._contract_repo.save(contract)

        logger.info(
            "draft_regenerated_with_final_reference",
            cr_id=str(cr.id),
            contract_id=str(saved.id),
            reference=cr.display_reference,
            s3_key=s3_key,
        )
        return saved
