"""SQLAlchemy models for the contract_management bounded context."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models import Base


class ContractRequestModel(Base):
    """Contract request SQLAlchemy model."""

    __tablename__ = "cm_contract_requests"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provisional_reference: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="Référence provisoire (PROV-YYYY-NNNN), générée à la création",
    )
    reference: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        comment="Référence définitive (XXX-CC-NNNN), assignée à l'état PARTNER_APPROVED",
    )
    trigger_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="What triggered this CR: positioning_7, candidat_11, ressource_4, ressource_5",
    )
    previous_contract_request_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_contract_requests.id"),
        nullable=True,
        comment="Link to previous CR for re-contractualization",
    )
    boond_positioning_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_consultant_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    boond_need_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_resource_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Boond resource ID for resource-triggered workflows",
    )
    third_party_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending_commercial_validation"
    )
    third_party_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    quantity_sold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultant_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    consultant_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mission_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mission_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contractualization_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    commercial_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commercial_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_companies.id"), nullable=True
    )
    compliance_override: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents_skipped: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Dépôt des documents de vigilance volontairement ignoré (saisie manuelle ADV)",
    )
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
    email_from: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email expediteur pour les mails lies a cette societe (ex: noreply@geminiconsulting.fr)",
    )
    tva_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Préfixe de référence (3 lettres, ex: "GEM") utilisé dans les références XXX-CC-NNNN
    code: Mapped[str] = mapped_column(String(3), nullable=False, default="GEN")
    # Identité visuelle
    color_code: Mapped[str] = mapped_column(String(7), nullable=False, default="#4BBEA8")
    logo_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    boond_agency_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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


class CharterTemplateModel(Base):
    """Charter template (charte/engagement) uploaded by admin."""

    __tablename__ = "cm_charter_templates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_contract_companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="partner or consultant",
    )
    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="charte",
        comment="charte, politique, document_unilateral, engagement, autre",
    )
    requires_acknowledgement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consultant_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="all",
        comment="all, external, internal — only relevant when target=consultant",
    )
    file_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ar_file_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ar_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SignatureUploadModel(Base):
    """Tracks individual signed documents for a contract request."""

    __tablename__ = "cm_signature_uploads"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    contract_request_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_contract_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    charter_template_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_charter_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="contract, charter_ar, charter_engagement",
    )
    signer_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="partner or consultant",
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CharterAcknowledgementModel(Base):
    """Record of a charter being acknowledged/signed."""

    __tablename__ = "cm_charter_acknowledgements"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    charter_template_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_charter_templates.id"), nullable=False
    )
    third_party_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=True
    )
    contract_request_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_requests.id"), nullable=True
    )
    consultant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="checkbox")
    yousign_envelope_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signed_document_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContractConsultantModel(Base):
    """Consultant linked to a contract for charter tracking."""

    __tablename__ = "cm_contract_consultants"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    contract_request_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_requests.id"), nullable=False
    )
    boond_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    charter_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending, sent, signed",
    )
    yousign_envelope_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PurchaseOrderModel(Base):
    """Purchase order (bon de commande) SQLAlchemy model.

    Une mission d'un consultant chez un client, rattachée au fournisseur et à
    son contrat cadre. `third_party_id` et `contract_request_id` sont nullables :
    un BDC créé par le webhook positionnement naît « à rattacher », l'ADV
    choisit ensuite le fournisseur.
    """

    __tablename__ = "cm_purchase_orders"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provisional_reference: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="Référence provisoire (PROV-BC-YYYY-NNN), assignée à la création",
    )
    reference: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        comment="Référence définitive (XXX-BC-NNN), assignée à la génération du document",
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    company_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cm_contract_companies.id"), nullable=True
    )
    third_party_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tp_third_parties.id"), nullable=True
    )
    contract_request_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_contract_requests.id"),
        nullable=True,
        comment="Contrat cadre de rattachement",
    )
    parent_purchase_order_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cm_purchase_orders.id"),
        nullable=True,
        comment="BDC d'origine en cas de reconduction",
    )

    # Consultant
    boond_consultant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_consultant_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consultant_civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    consultant_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultant_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Origine Boond
    boond_positioning_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_need_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_delivery_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Prestation Boond, support du renouvellement (POST /deliveries/{id}/renew)",
    )

    # Mission
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mission_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mission_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mission_city: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Conditions financières
    sale_daily_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="TJM de vente client — interne, jamais imprimé sur le document fournisseur",
    )
    purchase_daily_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="CJM d'achat fournisseur — le seul taux du bon de commande",
    )
    days_sold: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    free_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=0, server_default=text("0")
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Documents et signature
    s3_key_draft: Mapped[str | None] = mapped_column(String(500), nullable=True)
    s3_key_signed: Mapped[str | None] = mapped_column(String(500), nullable=True)
    yousign_envelope_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sent_for_signature_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Synchronisation Boond
    boond_contract_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_purchase_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boond_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    commercial_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
