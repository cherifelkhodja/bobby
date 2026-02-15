"""Port for vigilance document repository."""

from typing import Protocol
from uuid import UUID

from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType


class DocumentRepositoryPort(Protocol):
    """Repository port for vigilance documents."""

    async def get_by_id(self, document_id: UUID) -> VigilanceDocument | None:
        """Get a document by its ID."""
        ...

    async def save(self, document: VigilanceDocument) -> VigilanceDocument:
        """Save a document (create or update)."""
        ...

    async def list_by_third_party(
        self,
        third_party_id: UUID,
        status: DocumentStatus | None = None,
    ) -> list[VigilanceDocument]:
        """List documents for a third party, optionally filtered by status."""
        ...

    async def get_by_third_party_and_type(
        self,
        third_party_id: UUID,
        document_type: DocumentType,
    ) -> VigilanceDocument | None:
        """Get the latest document of a given type for a third party."""
        ...

    async def list_expiring(self, days_ahead: int = 30) -> list[VigilanceDocument]:
        """List documents expiring within the given number of days."""
        ...

    async def list_expired(self) -> list[VigilanceDocument]:
        """List all validated documents that have expired."""
        ...

    async def count_by_status(
        self, third_party_id: UUID
    ) -> dict[str, int]:
        """Count documents grouped by status for a third party."""
        ...

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID."""
        ...
