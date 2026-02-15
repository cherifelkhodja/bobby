"""S3 document storage adapter for vigilance documents."""

from datetime import datetime
from uuid import UUID

import structlog

logger = structlog.get_logger()


class VigilanceDocumentStorage:
    """S3 storage wrapper for vigilance documents.

    Organizes files as: vigilance/{third_party_id}/{document_type}/{id}_{timestamp}.{ext}
    """

    def __init__(self, s3_service) -> None:
        self._s3 = s3_service

    def _build_key(
        self,
        third_party_id: UUID,
        document_type: str,
        document_id: UUID,
        extension: str,
    ) -> str:
        """Build the S3 key for a vigilance document.

        Args:
            third_party_id: The third party UUID.
            document_type: Document type string.
            document_id: Document UUID.
            extension: File extension (e.g. 'pdf').

        Returns:
            The S3 key string.
        """
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"vigilance/{third_party_id}/{document_type}/{document_id}_{ts}.{extension}"

    async def upload(
        self,
        third_party_id: UUID,
        document_type: str,
        document_id: UUID,
        content: bytes,
        content_type: str,
        extension: str,
    ) -> str:
        """Upload a document to S3.

        Args:
            third_party_id: The third party UUID.
            document_type: Document type string.
            document_id: Document UUID.
            content: File content.
            content_type: MIME type.
            extension: File extension.

        Returns:
            The S3 key where the file was stored.
        """
        key = self._build_key(third_party_id, document_type, document_id, extension)
        await self._s3.upload_file(key=key, content=content, content_type=content_type)
        logger.info(
            "vigilance_document_uploaded_to_s3",
            s3_key=key,
            document_id=str(document_id),
            third_party_id=str(third_party_id),
        )
        return key

    async def get_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Get a presigned download URL for a document.

        Args:
            s3_key: The S3 key of the document.
            expires_in: URL expiration in seconds.

        Returns:
            Presigned URL.
        """
        return await self._s3.get_presigned_url(key=s3_key, expires_in=expires_in)

    async def delete(self, s3_key: str) -> bool:
        """Delete a document from S3.

        Args:
            s3_key: The S3 key of the document.

        Returns:
            True if deletion succeeded.
        """
        result = await self._s3.delete_file(key=s3_key)
        if result:
            logger.info("vigilance_document_deleted_from_s3", s3_key=s3_key)
        return result
