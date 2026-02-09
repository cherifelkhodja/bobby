"""Preview batch use case - Parse CSV and return preview."""

import logging
from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

from app.quotation_generator.domain.ports import BatchStoragePort
from app.quotation_generator.infrastructure.adapters.boond_adapter import (
    BoondManagerAdapter,
)
from app.quotation_generator.services.csv_parser import CSVParserService

logger = logging.getLogger(__name__)


@dataclass
class PreviewBatchResult:
    """Result of preview batch use case."""

    batch_id: UUID
    total_quotations: int
    valid_count: int
    invalid_count: int
    quotations: list[dict]
    validation_errors: dict[int, list[str]]


class PreviewBatchUseCase:
    """Use case for parsing CSV and generating preview.

    This use case:
    1. Parses the uploaded CSV file
    2. Validates all quotations
    3. Fetches available contacts for each company
    4. Stores the batch in Redis for later confirmation
    5. Returns preview data for the frontend
    """

    def __init__(
        self,
        csv_parser: CSVParserService,
        batch_storage: BatchStoragePort,
        boond_adapter: BoondManagerAdapter | None = None,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            csv_parser: Service for parsing CSV files.
            batch_storage: Storage for batch state.
            boond_adapter: Optional adapter for fetching contacts.
        """
        self.csv_parser = csv_parser
        self.batch_storage = batch_storage
        self.boond_adapter = boond_adapter

    async def execute(
        self,
        file: BinaryIO,
        user_id: UUID,
    ) -> PreviewBatchResult:
        """Execute the preview batch use case.

        Args:
            file: CSV file to parse.
            user_id: ID of the admin user.

        Returns:
            PreviewBatchResult with parsed data.

        Raises:
            CSVParsingError: If CSV parsing fails.
            MissingColumnsError: If required columns are missing.
        """
        logger.info(f"Starting preview batch for user {user_id}")

        # Parse CSV (async version supports enrichment from BoondManager)
        file_content = file.read()
        batch = await self.csv_parser.parse_async(file_content, user_id)

        # Validate all quotations
        validation_errors = batch.validate_all()

        # Count valid/invalid
        valid_count = sum(1 for q in batch.quotations if q.is_valid)
        invalid_count = batch.total_count - valid_count

        # Fetch available contacts for each company
        company_contacts: dict[str, list[dict]] = {}
        if self.boond_adapter:
            # Get unique company IDs
            unique_company_ids = {q.company_id for q in batch.quotations}
            for company_id in unique_company_ids:
                try:
                    contacts = await self.boond_adapter.get_company_contacts(company_id)
                    company_contacts[company_id] = contacts
                except Exception as e:
                    logger.warning(f"Failed to fetch contacts for company {company_id}: {e}")
                    company_contacts[company_id] = []

        # Store batch in Redis (1 hour TTL for preview)
        await self.batch_storage.save_batch(batch, ttl_seconds=3600)

        logger.info(
            f"Preview complete: {valid_count} valid, {invalid_count} invalid "
            f"out of {batch.total_count} quotations"
        )

        # Build quotations list with available_contacts
        quotations_preview = batch.to_preview_dict()["quotations"]
        for q in quotations_preview:
            company_id = q.get("company_id")
            q["available_contacts"] = company_contacts.get(company_id, [])

        return PreviewBatchResult(
            batch_id=batch.id,
            total_quotations=batch.total_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            quotations=quotations_preview,
            validation_errors=validation_errors,
        )
