"""Redis adapter implementing BatchStoragePort for batch state management."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from app.quotation_generator.domain.entities import (
    Quotation,
    QuotationBatch,
    QuotationLine,
)
from app.quotation_generator.domain.ports import BatchStoragePort
from app.quotation_generator.domain.value_objects import (
    BatchStatus,
    Money,
    Period,
    QuotationStatus,
)

logger = logging.getLogger(__name__)


class RedisStorageAdapter(BatchStoragePort):
    """Redis adapter for batch state storage.

    This adapter implements the BatchStoragePort interface to store
    and retrieve batch processing state using Redis.
    """

    # Key prefixes for Redis
    BATCH_KEY_PREFIX = "quotation_batch:"
    PROGRESS_KEY_PREFIX = "quotation_progress:"
    USER_BATCHES_KEY_PREFIX = "user_batches:"

    def __init__(self, redis_url: str) -> None:
        """Initialize adapter with Redis URL.

        Args:
            redis_url: Redis connection URL.
        """
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _batch_key(self, batch_id: UUID) -> str:
        """Generate Redis key for batch."""
        return f"{self.BATCH_KEY_PREFIX}{batch_id}"

    def _progress_key(self, batch_id: UUID) -> str:
        """Generate Redis key for progress."""
        return f"{self.PROGRESS_KEY_PREFIX}{batch_id}"

    def _user_batches_key(self, user_id: UUID) -> str:
        """Generate Redis key for user's batch list."""
        return f"{self.USER_BATCHES_KEY_PREFIX}{user_id}"

    def _serialize_batch(self, batch: QuotationBatch) -> str:
        """Serialize batch to JSON string."""
        return json.dumps(self._batch_to_dict(batch), default=self._json_encoder)

    def _deserialize_batch(self, data: str) -> QuotationBatch:
        """Deserialize batch from JSON string."""
        batch_dict = json.loads(data)
        return self._dict_to_batch(batch_dict)

    def _json_encoder(self, obj: Any) -> Any:
        """Custom JSON encoder for special types."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (BatchStatus, QuotationStatus)):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _batch_to_dict(self, batch: QuotationBatch) -> dict:
        """Convert batch to dictionary for serialization."""
        return {
            "id": str(batch.id),
            "user_id": str(batch.user_id),
            "status": batch.status.value,
            "created_at": batch.created_at.isoformat(),
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "merged_pdf_path": batch.merged_pdf_path,
            "zip_file_path": batch.zip_file_path,
            "error_message": batch.error_message,
            "quotations": [self._quotation_to_dict(q) for q in batch.quotations],
        }

    def _quotation_to_dict(self, quotation: Quotation) -> dict:
        """Convert quotation to dictionary."""
        return {
            "id": str(quotation.id),
            "row_index": quotation.row_index,
            "resource_id": quotation.resource_id,
            "resource_name": quotation.resource_name,
            "resource_trigramme": quotation.resource_trigramme,
            "opportunity_id": quotation.opportunity_id,
            "company_id": quotation.company_id,
            "company_name": quotation.company_name,
            "company_detail_id": quotation.company_detail_id,
            "contact_id": quotation.contact_id,
            "contact_name": quotation.contact_name,
            "period": {
                "start_date": quotation.period.start_date.isoformat(),
                "end_date": quotation.period.end_date.isoformat(),
            },
            "period_name": quotation.period_name,
            "quotation_date": quotation.quotation_date.isoformat()
            if quotation.quotation_date
            else None,
            "need_title": quotation.need_title,
            "line": {
                "description": quotation.line.description,
                "quantity": quotation.line.quantity,
                "unit_price_ht": str(quotation.line.unit_price_ht.amount),
                "tax_rate": str(quotation.line.tax_rate),
            },
            "sow_reference": quotation.sow_reference,
            "object_of_need": quotation.object_of_need,
            "c22_domain": quotation.c22_domain,
            "c22_activity": quotation.c22_activity,
            "complexity": quotation.complexity,
            "max_price": str(quotation.max_price.amount),
            "start_project": quotation.start_project.isoformat(),
            "comments": quotation.comments,
            "pdf_path": quotation.pdf_path,
            "status": quotation.status.value,
            "boond_quotation_id": quotation.boond_quotation_id,
            "boond_reference": quotation.boond_reference,
            "error_message": quotation.error_message,
            "validation_errors": quotation.validation_errors,
        }

    def _dict_to_batch(self, data: dict) -> QuotationBatch:
        """Convert dictionary to batch."""

        batch = QuotationBatch(
            user_id=UUID(data["user_id"]),
            id=UUID(data["id"]),
            status=BatchStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            merged_pdf_path=data.get("merged_pdf_path"),
            zip_file_path=data.get("zip_file_path"),
            error_message=data.get("error_message"),
        )

        for q_data in data.get("quotations", []):
            quotation = self._dict_to_quotation(q_data)
            batch.quotations.append(quotation)

        return batch

    def _dict_to_quotation(self, data: dict) -> Quotation:
        """Convert dictionary to quotation."""
        from datetime import date

        period_data = data["period"]
        line_data = data["line"]

        # Parse quotation_date if present
        quotation_date = None
        if data.get("quotation_date"):
            quotation_date = date.fromisoformat(data["quotation_date"])

        quotation = Quotation(
            id=UUID(data["id"]),
            row_index=data["row_index"],
            resource_id=data["resource_id"],
            resource_name=data["resource_name"],
            resource_trigramme=data["resource_trigramme"],
            opportunity_id=data["opportunity_id"],
            company_id=data["company_id"],
            company_name=data["company_name"],
            company_detail_id=data["company_detail_id"],
            contact_id=data["contact_id"],
            contact_name=data["contact_name"],
            period=Period(
                start_date=date.fromisoformat(period_data["start_date"]),
                end_date=date.fromisoformat(period_data["end_date"]),
            ),
            period_name=data.get("period_name", ""),
            quotation_date=quotation_date,
            need_title=data.get("need_title", ""),
            line=QuotationLine(
                description=line_data["description"],
                quantity=line_data["quantity"],
                unit_price_ht=Money(amount=Decimal(line_data["unit_price_ht"])),
                tax_rate=Decimal(line_data["tax_rate"]),
            ),
            sow_reference=data["sow_reference"],
            object_of_need=data["object_of_need"],
            c22_domain=data["c22_domain"],
            c22_activity=data["c22_activity"],
            complexity=data["complexity"],
            max_price=Money(amount=Decimal(data["max_price"])),
            start_project=date.fromisoformat(data["start_project"]),
            comments=data.get("comments"),
            pdf_path=data.get("pdf_path"),
            status=QuotationStatus(data["status"]),
            boond_quotation_id=data.get("boond_quotation_id"),
            boond_reference=data.get("boond_reference"),
            error_message=data.get("error_message"),
            validation_errors=data.get("validation_errors", []),
        )

        return quotation

    async def save_batch(self, batch: QuotationBatch, ttl_seconds: int = 3600) -> None:
        """Save or update a batch in Redis.

        Args:
            batch: The batch entity to save.
            ttl_seconds: Time-to-live in seconds (default 1 hour).
        """
        r = await self._get_redis()

        # Save full batch data
        batch_key = self._batch_key(batch.id)
        batch_data = self._serialize_batch(batch)
        await r.setex(batch_key, ttl_seconds, batch_data)

        # Save progress separately for fast access
        progress_key = self._progress_key(batch.id)
        progress_data = json.dumps(batch.to_progress_dict())
        await r.setex(progress_key, ttl_seconds, progress_data)

        # Add to user's batch list
        user_key = self._user_batches_key(batch.user_id)
        await r.zadd(
            user_key,
            {str(batch.id): batch.created_at.timestamp()},
        )
        await r.expire(user_key, ttl_seconds * 24)  # Keep user list longer

        logger.debug(f"Saved batch {batch.id} to Redis with TTL {ttl_seconds}s")

    async def get_batch(self, batch_id: UUID) -> QuotationBatch | None:
        """Retrieve a batch by ID.

        Args:
            batch_id: The batch UUID.

        Returns:
            The batch entity, or None if not found or expired.
        """
        r = await self._get_redis()
        batch_key = self._batch_key(batch_id)

        data = await r.get(batch_key)
        if not data:
            return None

        try:
            return self._deserialize_batch(data)
        except Exception as e:
            logger.error(f"Failed to deserialize batch {batch_id}: {e}")
            return None

    async def delete_batch(self, batch_id: UUID) -> bool:
        """Delete a batch from storage.

        Args:
            batch_id: The batch UUID.

        Returns:
            True if deleted, False if not found.
        """
        r = await self._get_redis()

        batch_key = self._batch_key(batch_id)
        progress_key = self._progress_key(batch_id)

        deleted = await r.delete(batch_key, progress_key)
        return deleted > 0

    async def update_batch_status(
        self,
        batch_id: UUID,
        status: str,
        progress: dict | None = None,
    ) -> bool:
        """Update batch status and progress.

        Args:
            batch_id: The batch UUID.
            status: New status value.
            progress: Optional progress dictionary.

        Returns:
            True if updated, False if batch not found.
        """
        r = await self._get_redis()

        # Get current batch
        batch = await self.get_batch(batch_id)
        if not batch:
            return False

        # Update status
        batch.status = BatchStatus(status)

        # Get remaining TTL
        batch_key = self._batch_key(batch_id)
        ttl = await r.ttl(batch_key)
        if ttl < 0:
            ttl = 3600  # Default 1 hour

        # Save updated batch
        await self.save_batch(batch, ttl_seconds=ttl)
        return True

    async def get_batch_progress(self, batch_id: UUID) -> dict | None:
        """Get batch progress without full deserialization.

        Args:
            batch_id: The batch UUID.

        Returns:
            Progress dictionary or None if not found.
        """
        r = await self._get_redis()
        progress_key = self._progress_key(batch_id)

        data = await r.get(progress_key)
        if not data:
            return None

        try:
            return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to parse progress for {batch_id}: {e}")
            return None

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
        r = await self._get_redis()
        user_key = self._user_batches_key(user_id)

        # Get most recent batch IDs
        batch_ids = await r.zrevrange(user_key, 0, limit - 1)

        batches = []
        for batch_id_str in batch_ids:
            progress = await self.get_batch_progress(UUID(batch_id_str))
            if progress:
                batches.append(progress)

        return batches

    async def extend_ttl(self, batch_id: UUID, ttl_seconds: int) -> bool:
        """Extend the TTL of a batch.

        Args:
            batch_id: The batch UUID.
            ttl_seconds: New TTL in seconds.

        Returns:
            True if extended, False if batch not found.
        """
        r = await self._get_redis()

        batch_key = self._batch_key(batch_id)
        progress_key = self._progress_key(batch_id)

        # Check if batch exists
        if not await r.exists(batch_key):
            return False

        await r.expire(batch_key, ttl_seconds)
        await r.expire(progress_key, ttl_seconds)
        return True

    async def save_zip_path(self, batch_id: UUID, zip_path: str) -> bool:
        """Save the ZIP file path for a completed batch.

        Args:
            batch_id: The batch UUID.
            zip_path: Path to the generated ZIP file.

        Returns:
            True if saved, False if batch not found.
        """
        batch = await self.get_batch(batch_id)
        if not batch:
            return False

        batch.zip_file_path = zip_path

        # Get remaining TTL
        r = await self._get_redis()
        batch_key = self._batch_key(batch_id)
        ttl = await r.ttl(batch_key)
        if ttl < 0:
            ttl = 3600

        await self.save_batch(batch, ttl_seconds=ttl)
        return True

    async def get_zip_path(self, batch_id: UUID) -> str | None:
        """Get the ZIP file path for a batch.

        Args:
            batch_id: The batch UUID.

        Returns:
            ZIP file path or None if not found.
        """
        progress = await self.get_batch_progress(batch_id)
        if not progress:
            return None
        return progress.get("zip_file_path")
