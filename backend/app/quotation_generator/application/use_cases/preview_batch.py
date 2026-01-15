"""Preview batch use case - Parse CSV and return preview."""

import logging
from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

from app.quotation_generator.domain.entities import QuotationBatch
from app.quotation_generator.domain.ports import BatchStoragePort
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
    3. Stores the batch in Redis for later confirmation
    4. Returns preview data for the frontend
    """

    def __init__(
        self,
        csv_parser: CSVParserService,
        batch_storage: BatchStoragePort,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            csv_parser: Service for parsing CSV files.
            batch_storage: Storage for batch state.
        """
        self.csv_parser = csv_parser
        self.batch_storage = batch_storage

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

        # Parse CSV
        batch = self.csv_parser.parse_file(file, user_id)

        # Validate all quotations
        validation_errors = batch.validate_all()

        # Count valid/invalid
        valid_count = sum(1 for q in batch.quotations if q.is_valid)
        invalid_count = batch.total_count - valid_count

        # Store batch in Redis (1 hour TTL for preview)
        await self.batch_storage.save_batch(batch, ttl_seconds=3600)

        logger.info(
            f"Preview complete: {valid_count} valid, {invalid_count} invalid "
            f"out of {batch.total_count} quotations"
        )

        return PreviewBatchResult(
            batch_id=batch.id,
            total_quotations=batch.total_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            quotations=batch.to_preview_dict()["quotations"],
            validation_errors=validation_errors,
        )
