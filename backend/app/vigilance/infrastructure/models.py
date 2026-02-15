"""SQLAlchemy models for the vigilance bounded context."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class VigilanceDocumentModel(Base):
    """Vigilance document SQLAlchemy model."""

    __tablename__ = "vig_documents"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    third_party_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_check_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
