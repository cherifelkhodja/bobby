"""PostgreSQL implementation of DocumentRepository."""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.vigilance.domain.entities.vigilance_document import VigilanceDocument
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.domain.value_objects.document_type import DocumentType
from app.vigilance.infrastructure.models import VigilanceDocumentModel

logger = structlog.get_logger()


class DocumentRepository:
    """PostgreSQL-backed vigilance document repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, document_id: UUID) -> VigilanceDocument | None:
        """Get a document by its ID."""
        result = await self.session.execute(
            select(VigilanceDocumentModel).where(VigilanceDocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, document: VigilanceDocument) -> VigilanceDocument:
        """Save a document (create or update)."""
        result = await self.session.execute(
            select(VigilanceDocumentModel).where(VigilanceDocumentModel.id == document.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.status = document.status.value
            model.s3_key = document.s3_key
            model.file_name = document.file_name
            model.file_size = document.file_size
            model.uploaded_at = document.uploaded_at
            model.validated_at = document.validated_at
            model.validated_by = document.validated_by
            model.rejected_at = document.rejected_at
            model.rejection_reason = document.rejection_reason
            model.expires_at = document.expires_at
            model.auto_check_results = document.auto_check_results
            model.updated_at = document.updated_at
        else:
            model = self._to_model(document)
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def list_by_third_party(
        self,
        third_party_id: UUID,
        status: DocumentStatus | None = None,
    ) -> list[VigilanceDocument]:
        """List documents for a third party, optionally filtered by status."""
        query = select(VigilanceDocumentModel).where(
            VigilanceDocumentModel.third_party_id == third_party_id
        )
        if status:
            query = query.where(VigilanceDocumentModel.status == status.value)

        query = query.order_by(VigilanceDocumentModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_third_party_and_type(
        self,
        third_party_id: UUID,
        document_type: DocumentType,
    ) -> VigilanceDocument | None:
        """Get the latest document of a given type for a third party."""
        result = await self.session.execute(
            select(VigilanceDocumentModel)
            .where(
                VigilanceDocumentModel.third_party_id == third_party_id,
                VigilanceDocumentModel.document_type == document_type.value,
            )
            .order_by(VigilanceDocumentModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_expiring(self, days_ahead: int = 30) -> list[VigilanceDocument]:
        """List documents expiring within the given number of days."""
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)
        result = await self.session.execute(
            select(VigilanceDocumentModel)
            .where(
                VigilanceDocumentModel.status == DocumentStatus.VALIDATED.value,
                VigilanceDocumentModel.expires_at.isnot(None),
                VigilanceDocumentModel.expires_at <= cutoff,
                VigilanceDocumentModel.expires_at > now,
            )
            .order_by(VigilanceDocumentModel.expires_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_expired(self) -> list[VigilanceDocument]:
        """List all validated/expiring documents that have expired."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(VigilanceDocumentModel)
            .where(
                VigilanceDocumentModel.status.in_([
                    DocumentStatus.VALIDATED.value,
                    DocumentStatus.EXPIRING_SOON.value,
                ]),
                VigilanceDocumentModel.expires_at.isnot(None),
                VigilanceDocumentModel.expires_at <= now,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_status(self, third_party_id: UUID) -> dict[str, int]:
        """Count documents grouped by status for a third party."""
        query = (
            select(
                VigilanceDocumentModel.status,
                func.count(VigilanceDocumentModel.id),
            )
            .where(VigilanceDocumentModel.third_party_id == third_party_id)
            .group_by(VigilanceDocumentModel.status)
        )
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID."""
        result = await self.session.execute(
            select(VigilanceDocumentModel).where(VigilanceDocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False

    def _to_entity(self, model: VigilanceDocumentModel) -> VigilanceDocument:
        """Convert SQLAlchemy model to domain entity."""
        return VigilanceDocument(
            id=model.id,
            third_party_id=model.third_party_id,
            document_type=DocumentType(model.document_type),
            status=DocumentStatus(model.status),
            s3_key=model.s3_key,
            file_name=model.file_name,
            file_size=model.file_size,
            uploaded_at=model.uploaded_at,
            validated_at=model.validated_at,
            validated_by=model.validated_by,
            rejected_at=model.rejected_at,
            rejection_reason=model.rejection_reason,
            expires_at=model.expires_at,
            auto_check_results=model.auto_check_results,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: VigilanceDocument) -> VigilanceDocumentModel:
        """Convert domain entity to SQLAlchemy model."""
        return VigilanceDocumentModel(
            id=entity.id,
            third_party_id=entity.third_party_id,
            document_type=entity.document_type.value,
            status=entity.status.value,
            s3_key=entity.s3_key,
            file_name=entity.file_name,
            file_size=entity.file_size,
            uploaded_at=entity.uploaded_at,
            validated_at=entity.validated_at,
            validated_by=entity.validated_by,
            rejected_at=entity.rejected_at,
            rejection_reason=entity.rejection_reason,
            expires_at=entity.expires_at,
            auto_check_results=entity.auto_check_results,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
