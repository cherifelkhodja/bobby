"""Generate batch use case - Async quotation generation."""

import asyncio
import logging
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from uuid import UUID

from app.quotation_generator.domain.entities import QuotationBatch
from app.quotation_generator.domain.exceptions import (
    BatchNotFoundError,
    BoondManagerAPIError,
    PDFConversionError,
)
from app.quotation_generator.domain.ports import (
    BatchStoragePort,
    ERPPort,
    PDFConverterPort,
    TemplateRepositoryPort,
)
from app.quotation_generator.domain.value_objects import BatchStatus, QuotationStatus
from app.quotation_generator.services.template_filler import TemplateFillerService

logger = logging.getLogger(__name__)


class GenerateBatchUseCase:
    """Use case for generating quotations asynchronously.

    This use case:
    1. Retrieves the batch from storage
    2. For each quotation:
       a. Creates quotation in BoondManager
       b. Fills the PSTF Excel template
       c. Converts Excel to PDF
    3. Merges all PDFs into one per quotation
    4. Creates ZIP archive
    5. Updates batch status throughout
    """

    def __init__(
        self,
        batch_storage: BatchStoragePort,
        erp_adapter: ERPPort,
        template_repository: TemplateRepositoryPort,
        pdf_converter: PDFConverterPort,
        template_filler: TemplateFillerService,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            batch_storage: Storage for batch state.
            erp_adapter: Adapter for ERP operations.
            template_repository: Repository for templates.
            pdf_converter: Adapter for PDF conversion.
            template_filler: Service for filling templates.
            output_dir: Directory for output files.
        """
        self.batch_storage = batch_storage
        self.erp_adapter = erp_adapter
        self.template_repository = template_repository
        self.pdf_converter = pdf_converter
        self.template_filler = template_filler
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "quotations"

    async def execute(
        self,
        batch_id: UUID,
        template_name: str = "thales_pstf",
    ) -> None:
        """Execute the generate batch use case.

        This method runs asynchronously and updates batch status
        as it processes each quotation.

        Args:
            batch_id: ID of the batch to generate.
            template_name: Name of the template to use.

        Raises:
            BatchNotFoundError: If batch not found.
            TemplateNotFoundError: If template not found.
        """
        logger.info(f"Starting batch generation for {batch_id}")

        # Get batch from storage
        batch = await self.batch_storage.get_batch(batch_id)
        if not batch:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        # Get template
        template_content = await self.template_repository.get_template(template_name)
        if not template_content:
            batch.mark_failed(f"Template not found: {template_name}")
            await self.batch_storage.save_batch(batch)
            return

        # Create output directory for this batch
        batch_output_dir = self.output_dir / str(batch_id)
        batch_output_dir.mkdir(parents=True, exist_ok=True)

        # Start processing
        batch.start_processing()
        await self.batch_storage.save_batch(batch)

        # Process each quotation
        generated_files: list[Path] = []

        for quotation in batch.quotations:
            try:
                # Skip invalid quotations
                if not quotation.is_valid:
                    quotation.mark_as_failed("Validation errors")
                    await self._update_progress(batch)
                    continue

                # Mark as processing
                quotation.mark_as_processing(QuotationStatus.CREATING_BOOND)
                await self._update_progress(batch)

                # Step 1: Create quotation in BoondManager
                boond_id, boond_reference = await self.erp_adapter.create_quotation(
                    quotation
                )

                # Step 2: Fill template
                quotation.mark_as_processing(QuotationStatus.FILLING_TEMPLATE)
                await self._update_progress(batch)

                filled_template = self.template_filler.fill_template(
                    template_content,
                    quotation,
                    boond_reference,
                )

                # Save filled Excel
                excel_filename = f"{quotation.resource_trigramme}_{boond_reference}.xlsx"
                excel_path = batch_output_dir / excel_filename
                excel_path.write_bytes(filled_template)

                # Step 3: Convert to PDF
                quotation.mark_as_processing(QuotationStatus.CONVERTING_PDF)
                await self._update_progress(batch)

                pdf_path = await self.pdf_converter.convert_to_pdf(excel_path)
                generated_files.append(pdf_path)

                # Mark as completed
                quotation.mark_as_completed(boond_id, boond_reference)
                await self._update_progress(batch)

                logger.info(
                    f"Generated quotation {quotation.resource_trigramme}: "
                    f"BoondID={boond_id}, Ref={boond_reference}"
                )

            except BoondManagerAPIError as e:
                logger.error(f"BoondManager error for {quotation.resource_trigramme}: {e}")
                quotation.mark_as_failed(f"BoondManager error: {e.message}")
                await self._update_progress(batch)

            except PDFConversionError as e:
                logger.error(f"PDF conversion error for {quotation.resource_trigramme}: {e}")
                quotation.mark_as_failed(f"PDF conversion error: {str(e)}")
                await self._update_progress(batch)

            except Exception as e:
                logger.error(
                    f"Unexpected error for {quotation.resource_trigramme}: {e}",
                    exc_info=True,
                )
                quotation.mark_as_failed(f"Unexpected error: {str(e)}")
                await self._update_progress(batch)

        # Create ZIP archive
        if generated_files:
            zip_path = await self._create_zip_archive(batch, generated_files)

            if batch.has_errors:
                batch.mark_partial(str(zip_path))
            else:
                batch.mark_completed(str(zip_path))
        else:
            batch.mark_failed("No quotations were successfully generated")

        # Final save with extended TTL (24 hours for download)
        await self.batch_storage.save_batch(batch, ttl_seconds=86400)

        logger.info(
            f"Batch {batch_id} complete: {batch.completed_count}/{batch.total_count} "
            f"successful, status={batch.status.value}"
        )

    async def _update_progress(self, batch: QuotationBatch) -> None:
        """Update batch progress in storage.

        Args:
            batch: Batch to update.
        """
        await self.batch_storage.save_batch(batch)

    async def _create_zip_archive(
        self,
        batch: QuotationBatch,
        pdf_files: list[Path],
    ) -> Path:
        """Create ZIP archive with generated PDFs.

        Args:
            batch: The batch being processed.
            pdf_files: List of PDF file paths.

        Returns:
            Path to the ZIP archive.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"devis_thales_{timestamp}.zip"
        zip_path = self.output_dir / str(batch.id) / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for pdf_path in pdf_files:
                zipf.write(pdf_path, pdf_path.name)

        logger.info(f"Created ZIP archive: {zip_path} with {len(pdf_files)} files")
        return zip_path


class StartGenerationUseCase:
    """Use case to start batch generation in background."""

    def __init__(
        self,
        batch_storage: BatchStoragePort,
        generate_use_case_factory: Callable[[], GenerateBatchUseCase],
    ) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
            generate_use_case_factory: Factory to create GenerateBatchUseCase with fresh DB session.
        """
        self.batch_storage = batch_storage
        self.generate_use_case_factory = generate_use_case_factory

    async def execute(
        self,
        batch_id: UUID,
        template_name: str = "thales_pstf",
    ) -> dict:
        """Start batch generation and return immediately.

        Args:
            batch_id: ID of the batch to generate.
            template_name: Name of the template to use.

        Returns:
            Dictionary with batch_id and status.

        Raises:
            BatchNotFoundError: If batch not found.
        """
        # Verify batch exists
        batch = await self.batch_storage.get_batch(batch_id)
        if not batch:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        # Update status to indicate generation starting
        batch.status = BatchStatus.PENDING
        await self.batch_storage.save_batch(batch)

        # Start generation in background with a fresh use case (new DB session)
        asyncio.create_task(
            self._run_generation(batch_id, template_name)
        )

        return {
            "batch_id": str(batch_id),
            "status": "started",
            "total_quotations": batch.total_count,
        }

    async def _run_generation(self, batch_id: UUID, template_name: str) -> None:
        """Run generation with a fresh use case instance.

        This creates a new DB session for the background task.
        """
        try:
            # Create fresh use case with new DB session
            generate_use_case = self.generate_use_case_factory()

            # Execute with proper session management
            session = generate_use_case.template_repository.session
            try:
                await generate_use_case.execute(batch_id, template_name)
            finally:
                # Close the session when done
                await session.close()
        except Exception as e:
            logger.error(f"Background generation failed: {e}", exc_info=True)
            # Try to mark batch as failed
            try:
                batch = await self.batch_storage.get_batch(batch_id)
                if batch and batch.status != BatchStatus.COMPLETED:
                    batch.mark_failed(f"Generation error: {str(e)}")
                    await self.batch_storage.save_batch(batch)
            except Exception:
                pass
