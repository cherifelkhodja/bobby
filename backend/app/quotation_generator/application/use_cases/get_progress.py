"""Get batch progress use case."""

import logging
from typing import Optional
from uuid import UUID

from app.quotation_generator.domain.exceptions import BatchNotFoundError
from app.quotation_generator.domain.ports import BatchStoragePort

logger = logging.getLogger(__name__)


class GetBatchProgressUseCase:
    """Use case for getting batch generation progress.

    This use case retrieves the current progress of a batch
    from storage without full deserialization.
    """

    def __init__(self, batch_storage: BatchStoragePort) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
        """
        self.batch_storage = batch_storage

    async def execute(self, batch_id: UUID) -> dict:
        """Get batch progress.

        Args:
            batch_id: ID of the batch.

        Returns:
            Dictionary with progress information:
            - batch_id: str
            - status: str
            - total: int
            - completed: int
            - failed: int
            - pending: int
            - progress_percentage: float
            - is_complete: bool
            - has_errors: bool
            - zip_file_path: str | None
            - error_message: str | None

        Raises:
            BatchNotFoundError: If batch not found.
        """
        progress = await self.batch_storage.get_batch_progress(batch_id)

        if not progress:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        return progress


class GetBatchDetailsUseCase:
    """Use case for getting full batch details including quotation status."""

    def __init__(self, batch_storage: BatchStoragePort) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
        """
        self.batch_storage = batch_storage

    async def execute(self, batch_id: UUID) -> dict:
        """Get full batch details.

        Args:
            batch_id: ID of the batch.

        Returns:
            Dictionary with full batch information including
            individual quotation statuses.

        Raises:
            BatchNotFoundError: If batch not found.
        """
        batch = await self.batch_storage.get_batch(batch_id)

        if not batch:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        # Build detailed response
        quotations = []
        for q in batch.quotations:
            quotations.append({
                "row_index": q.row_index,
                "resource_name": q.resource_name,
                "resource_trigramme": q.resource_trigramme,
                "opportunity_id": q.opportunity_id,
                "company_name": q.company_name,
                "status": q.status.value,
                "boond_quotation_id": q.boond_quotation_id,
                "boond_reference": q.boond_reference,
                "error_message": q.error_message,
                "is_valid": q.is_valid,
                "validation_errors": q.validation_errors,
            })

        return {
            "batch_id": str(batch.id),
            "user_id": str(batch.user_id),
            "status": batch.status.value,
            "created_at": batch.created_at.isoformat(),
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "total": batch.total_count,
            "completed": batch.completed_count,
            "failed": batch.failed_count,
            "pending": batch.pending_count,
            "progress_percentage": round(batch.progress_percentage, 1),
            "is_complete": batch.is_complete,
            "has_errors": batch.has_errors,
            "zip_file_path": batch.zip_file_path,
            "error_message": batch.error_message,
            "quotations": quotations,
        }


class ListUserBatchesUseCase:
    """Use case for listing recent batches for a user."""

    def __init__(self, batch_storage: BatchStoragePort) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
        """
        self.batch_storage = batch_storage

    async def execute(self, user_id: UUID, limit: int = 10) -> list[dict]:
        """List recent batches for a user.

        Args:
            user_id: ID of the user.
            limit: Maximum number of batches to return.

        Returns:
            List of batch summary dictionaries.
        """
        return await self.batch_storage.list_user_batches(user_id, limit)
