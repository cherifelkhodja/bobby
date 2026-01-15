"""Batch storage port interface for batch state management."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.quotation_generator.domain.entities import QuotationBatch


class BatchStoragePort(ABC):
    """Interface for batch state storage (Redis).

    This port defines the contract for storing and retrieving
    batch processing state for async job tracking.
    """

    @abstractmethod
    async def save_batch(self, batch: QuotationBatch, ttl_seconds: int = 3600) -> None:
        """Save or update a batch in storage.

        Args:
            batch: The batch entity to save.
            ttl_seconds: Time-to-live in seconds (default 1 hour).

        Raises:
            BatchStorageError: If save fails.
        """
        ...

    @abstractmethod
    async def get_batch(self, batch_id: UUID) -> Optional[QuotationBatch]:
        """Retrieve a batch by ID.

        Args:
            batch_id: The batch UUID.

        Returns:
            The batch entity, or None if not found or expired.
        """
        ...

    @abstractmethod
    async def delete_batch(self, batch_id: UUID) -> bool:
        """Delete a batch from storage.

        Args:
            batch_id: The batch UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def update_batch_status(
        self,
        batch_id: UUID,
        status: str,
        progress: Optional[dict] = None,
    ) -> bool:
        """Update batch status and progress.

        This is an optimized update for progress tracking
        that doesn't require deserializing the full batch.

        Args:
            batch_id: The batch UUID.
            status: New status value.
            progress: Optional progress dictionary with:
                - completed: int
                - failed: int
                - current_item: str

        Returns:
            True if updated, False if batch not found.
        """
        ...

    @abstractmethod
    async def get_batch_progress(self, batch_id: UUID) -> Optional[dict]:
        """Get batch progress without full deserialization.

        Args:
            batch_id: The batch UUID.

        Returns:
            Progress dictionary or None if not found.
        """
        ...

    @abstractmethod
    async def list_user_batches(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[dict]:
        """List recent batches for a user.

        Args:
            user_id: The user UUID.
            limit: Maximum number of batches to return.

        Returns:
            List of batch summary dictionaries.
        """
        ...

    @abstractmethod
    async def extend_ttl(self, batch_id: UUID, ttl_seconds: int) -> bool:
        """Extend the TTL of a batch.

        Args:
            batch_id: The batch UUID.
            ttl_seconds: New TTL in seconds.

        Returns:
            True if extended, False if batch not found.
        """
        ...

    @abstractmethod
    async def save_zip_path(self, batch_id: UUID, zip_path: str) -> bool:
        """Save the ZIP file path for a completed batch.

        Args:
            batch_id: The batch UUID.
            zip_path: Path to the generated ZIP file.

        Returns:
            True if saved, False if batch not found.
        """
        ...

    @abstractmethod
    async def get_zip_path(self, batch_id: UUID) -> Optional[str]:
        """Get the ZIP file path for a batch.

        Args:
            batch_id: The batch UUID.

        Returns:
            ZIP file path or None if not found.
        """
        ...
