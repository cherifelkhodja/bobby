"""SQLAlchemy models for the third_party bounded context."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models import Base


class ThirdPartyModel(Base):
    """Third party (freelance / subcontractor) SQLAlchemy model."""

    __tablename__ = "tp_third_parties"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    boond_provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capital: Mapped[str | None] = mapped_column(String(50), nullable=True)
    siren: Mapped[str | None] = mapped_column(String(9), nullable=True)
    siret: Mapped[str | None] = mapped_column(String(14), nullable=True)
    rcs_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rcs_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    head_office_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_office_street: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_office_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    head_office_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    representative_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representative_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representative_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    representative_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    representative_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    representative_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representative_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signatory_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    signatory_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signatory_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signatory_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signatory_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signatory_is_director: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adv_contact_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    adv_contact_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adv_contact_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adv_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adv_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_contact_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    billing_contact_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_contact_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ape_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    entity_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company_info_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    magic_links: Mapped[list["MagicLinkModel"]] = relationship(
        "MagicLinkModel", back_populates="third_party", lazy="selectin"
    )


class MagicLinkModel(Base):
    """Magic link SQLAlchemy model."""

    __tablename__ = "tp_magic_links"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    third_party_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=False
    )
    contract_request_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_requests.id"), nullable=True
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    email_sent_to: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    third_party: Mapped["ThirdPartyModel"] = relationship(
        "ThirdPartyModel", back_populates="magic_links"
    )
