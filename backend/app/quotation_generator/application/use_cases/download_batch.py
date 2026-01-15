"""Download batch use case."""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.quotation_generator.domain.exceptions import (
    BatchNotFoundError,
    DownloadNotReadyError,
)
from app.quotation_generator.domain.ports import BatchStoragePort
from app.quotation_generator.domain.value_objects import BatchStatus

logger = logging.getLogger(__name__)


class DownloadBatchUseCase:
    """Use case for downloading generated batch ZIP file.

    This use case:
    1. Verifies the batch exists and is complete
    2. Returns the path to the ZIP file for streaming
    """

    def __init__(self, batch_storage: BatchStoragePort) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
        """
        self.batch_storage = batch_storage

    async def execute(self, batch_id: UUID) -> Path:
        """Get ZIP file path for download.

        Args:
            batch_id: ID of the batch.

        Returns:
            Path to the ZIP file.

        Raises:
            BatchNotFoundError: If batch not found.
            DownloadNotReadyError: If batch not complete or no ZIP file.
        """
        logger.info(f"Download requested for batch {batch_id}")

        # Get batch progress
        progress = await self.batch_storage.get_batch_progress(batch_id)

        if not progress:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        # Check if batch is complete
        status = progress.get("status")
        if status not in [BatchStatus.COMPLETED.value, BatchStatus.PARTIAL.value]:
            raise DownloadNotReadyError(
                f"Batch is not ready for download. Status: {status}"
            )

        # Get ZIP path
        zip_path_str = progress.get("zip_file_path")
        if not zip_path_str:
            raise DownloadNotReadyError("No ZIP file available for this batch")

        zip_path = Path(zip_path_str)
        if not zip_path.exists():
            raise DownloadNotReadyError(f"ZIP file not found: {zip_path}")

        logger.info(f"Returning ZIP file: {zip_path}")
        return zip_path


class GetDownloadInfoUseCase:
    """Use case for getting download information without returning file."""

    def __init__(self, batch_storage: BatchStoragePort) -> None:
        """Initialize use case.

        Args:
            batch_storage: Storage for batch state.
        """
        self.batch_storage = batch_storage

    async def execute(self, batch_id: UUID) -> dict:
        """Get download information for a batch.

        Args:
            batch_id: ID of the batch.

        Returns:
            Dictionary with download info:
            - is_ready: bool
            - filename: str | None
            - file_size: int | None
            - completed_count: int
            - failed_count: int

        Raises:
            BatchNotFoundError: If batch not found.
        """
        progress = await self.batch_storage.get_batch_progress(batch_id)

        if not progress:
            raise BatchNotFoundError(f"Batch not found: {batch_id}")

        result = {
            "is_ready": False,
            "filename": None,
            "file_size": None,
            "completed_count": progress.get("completed", 0),
            "failed_count": progress.get("failed", 0),
        }

        status = progress.get("status")
        if status in [BatchStatus.COMPLETED.value, BatchStatus.PARTIAL.value]:
            zip_path_str = progress.get("zip_file_path")
            if zip_path_str:
                zip_path = Path(zip_path_str)
                if zip_path.exists():
                    result["is_ready"] = True
                    result["filename"] = zip_path.name
                    result["file_size"] = zip_path.stat().st_size

        return result
