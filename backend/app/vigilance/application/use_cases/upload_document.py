"""Use case: Upload a document for a third party."""

import os
from uuid import UUID

import structlog

from app.vigilance.domain.exceptions import (
    DocumentNotAllowedError,
    DocumentNotFoundError,
)
from app.vigilance.domain.services.vigilance_requirements import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
)
from app.vigilance.domain.value_objects.document_type import (
    FORBIDDEN_DOCUMENT_TYPES,
)

logger = structlog.get_logger()


class UploadDocumentCommand:
    """Command data for uploading a document."""

    def __init__(
        self,
        *,
        document_id: UUID,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> None:
        self.document_id = document_id
        self.file_content = file_content
        self.file_name = file_name
        self.content_type = content_type


class UploadDocumentUseCase:
    """Upload a document file to S3 and update the document status.

    Validates file format, size, RGPD rules, then uploads to S3
    and transitions document to RECEIVED.
    """

    def __init__(self, document_repository, document_storage) -> None:
        self._document_repo = document_repository
        self._document_storage = document_storage

    async def execute(self, command: UploadDocumentCommand):
        """Execute the use case.

        Args:
            command: Upload command with file data.

        Returns:
            The updated document entity.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotAllowedError: If the document type is forbidden.
            ValueError: If the file fails validation.
        """
        document = await self._document_repo.get_by_id(command.document_id)
        if not document:
            raise DocumentNotFoundError(str(command.document_id))

        # RGPD check
        if document.document_type.value in FORBIDDEN_DOCUMENT_TYPES:
            raise DocumentNotAllowedError(document.document_type.value)

        # File validation
        self._validate_file(command)

        # Extract extension
        _, ext = os.path.splitext(command.file_name)
        extension = ext.lstrip(".").lower() or "pdf"

        # Upload to S3
        s3_key = await self._document_storage.upload(
            third_party_id=document.third_party_id,
            document_type=document.document_type.value,
            document_id=document.id,
            content=command.file_content,
            content_type=command.content_type,
            extension=extension,
        )

        # Transition to RECEIVED
        document.mark_received(
            s3_key=s3_key,
            file_name=command.file_name,
            file_size=len(command.file_content),
        )

        saved = await self._document_repo.save(document)

        logger.info(
            "document_uploaded",
            document_id=str(saved.id),
            third_party_id=str(saved.third_party_id),
            document_type=saved.document_type.value,
            file_name=command.file_name,
            file_size=len(command.file_content),
        )

        return saved

    def _validate_file(self, command: UploadDocumentCommand) -> None:
        """Validate file format, size, and extension.

        Args:
            command: The upload command.

        Raises:
            ValueError: If validation fails.
        """
        if len(command.file_content) > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Fichier trop volumineux ({len(command.file_content)} octets). "
                f"Maximum autorisé : {MAX_FILE_SIZE_BYTES // (1024 * 1024)} Mo."
            )

        if command.content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Type de fichier non autorisé : {command.content_type}. "
                f"Types acceptés : {', '.join(ALLOWED_MIME_TYPES)}."
            )

        _, ext = os.path.splitext(command.file_name)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Extension de fichier non autorisée : {ext}. "
                f"Extensions acceptées : {', '.join(ALLOWED_EXTENSIONS)}."
            )
