"""SQLAlchemy models for the contract_management bounded context."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models import Base


class ContractRequestModel(Base):
    """Contract request SQLAlchemy model."""

    __tablename__ = "cm_contract_requests"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    boond_positioning_id: Mapped[int] = mapped_column(Integer, nullable=False)
    boond_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_need_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    third_party_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending_commercial_validation"
    )
    third_party_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultant_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    consultant_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mission_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contractualization_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    commercial_email: Mapped[str] = mapped_column(String(255), nullable=False)
    commercial_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_companies.id"), nullable=True
    )
    compliance_override: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContractModel(Base):
    """Contract document SQLAlchemy model."""

    __tablename__ = "cm_contracts"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    contract_request_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_requests.id"), nullable=False
    )
    third_party_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    s3_key_draft: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_key_signed: Mapped[str | None] = mapped_column(String(500), nullable=True)
    yousign_procedure_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yousign_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    boond_purchase_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partner_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ContractArticleTemplateModel(Base):
    """Contract article template SQLAlchemy model."""

    __tablename__ = "cm_contract_article_templates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    article_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    article_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class ContractCompanyModel(Base):
    """Issuing company for contracts (société émettrice du contrat)."""

    __tablename__ = "cm_contract_companies"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_form: Mapped[str] = mapped_column(String(50), nullable=False)
    capital: Mapped[str] = mapped_column(String(100), nullable=False)
    head_office: Mapped[str] = mapped_column(String(500), nullable=False)
    rcs_city: Mapped[str] = mapped_column(String(100), nullable=False)
    rcs_number: Mapped[str] = mapped_column(String(50), nullable=False)
    # Representative — personne physique ou morale
    representative_is_entity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    representative_name: Mapped[str] = mapped_column(String(255), nullable=False)
    representative_quality: Mapped[str] = mapped_column(String(255), nullable=False)
    # Champs supplémentaires si le représentant est une personne morale
    representative_sub_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representative_sub_quality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Bloc signature
    signatory_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Facturation
    invoices_company_mail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Identité visuelle
    color_code: Mapped[str] = mapped_column(String(7), nullable=False, default="#4BBEA8")
    logo_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContractAnnexTemplateModel(Base):
    """Contract annex template SQLAlchemy model."""

    __tablename__ = "cm_contract_annex_templates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    annexe_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    annexe_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_conditional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    condition_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class WebhookEventModel(Base):
    """Webhook event deduplication model."""

    __tablename__ = "cm_webhook_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
