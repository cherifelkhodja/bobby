"""SQLAlchemy ORM models."""

from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class UserModel(Base):
    """User database model."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    boond_resource_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manager_boond_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cooptations: Mapped[list["CooptationModel"]] = relationship(
        "CooptationModel", back_populates="submitter"
    )


class CandidateModel(Base):
    """Candidate database model."""

    __tablename__ = "candidates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    civility: Mapped[str] = mapped_column(String(10), default="M")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    daily_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cooptations: Mapped[list["CooptationModel"]] = relationship(
        "CooptationModel", back_populates="candidate"
    )


class OpportunityModel(Base):
    """Opportunity database model."""

    __tablename__ = "opportunities"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    response_deadline: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manager_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_boond_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)  # Shared for cooptation
    owner_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cooptations: Mapped[list["CooptationModel"]] = relationship(
        "CooptationModel", back_populates="opportunity"
    )
    owner: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[owner_id])


class CooptationModel(Base):
    """Cooptation database model."""

    __tablename__ = "cooptations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=False
    )
    submitter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    external_positioning_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    candidate: Mapped["CandidateModel"] = relationship(
        "CandidateModel", back_populates="cooptations"
    )
    opportunity: Mapped["OpportunityModel"] = relationship(
        "OpportunityModel", back_populates="cooptations"
    )
    submitter: Mapped["UserModel"] = relationship("UserModel", back_populates="cooptations")


class InvitationModel(Base):
    """Invitation database model."""

    __tablename__ = "invitations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    invited_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    boond_resource_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manager_boond_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    inviter: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[invited_by])


class BusinessLeadModel(Base):
    """Business Lead database model."""

    __tablename__ = "business_leads"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    submitter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    skills_needed: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    submitter: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[submitter_id])


class CvTemplateModel(Base):
    """CV Template database model."""

    __tablename__ = "cv_templates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CvTransformationLogModel(Base):
    """CV Transformation Log database model."""

    __tablename__ = "cv_transformation_logs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    template_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cv_templates.id"), nullable=True
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[user_id])
    template: Mapped[Optional["CvTemplateModel"]] = relationship(
        "CvTemplateModel", foreign_keys=[template_id]
    )


class PublishedOpportunityModel(Base):
    """Published Opportunity database model for anonymized opportunities."""

    __tablename__ = "published_opportunities"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    boond_opportunity_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list | None] = mapped_column(ARRAY(String(100)), nullable=True)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published", index=True)
    published_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    publisher: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[published_by])


class JobPostingModel(Base):
    """Job Posting database model for HR recruitment."""

    __tablename__ = "job_postings"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    opportunity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    qualifications: Mapped[str] = mapped_column(Text, nullable=False)
    location_country: Mapped[str] = mapped_column(String(50), nullable=False)
    location_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_key: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # Turnover-IT location key
    contract_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remote: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min_annual: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_annual: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_min_daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    employer_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    turnoverit_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )
    turnoverit_public_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    application_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    opportunity: Mapped["OpportunityModel"] = relationship("OpportunityModel")
    creator: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[created_by])
    applications: Mapped[list["JobApplicationModel"]] = relationship(
        "JobApplicationModel", back_populates="job_posting", cascade="all, delete-orphan"
    )


class JobApplicationModel(Base):
    """Job Application database model for candidates applying via public form."""

    __tablename__ = "job_applications"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_posting_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)

    # New fields for availability and status
    availability: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # asap, 1_month, etc.
    employment_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # freelance, employee, both
    english_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # notions, intermediate, etc.

    # New salary fields
    tjm_current: Mapped[float | None] = mapped_column(Float, nullable=True)
    tjm_desired: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_current: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_desired: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Legacy fields (kept for backward compatibility)
    tjm_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    tjm_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    cv_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    cv_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    matching_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matching_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cv_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cv_quality: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="en_cours", index=True)
    status_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    boond_candidate_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    civility: Mapped[str | None] = mapped_column(String(10), nullable=True)
    boond_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    boond_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    job_posting: Mapped["JobPostingModel"] = relationship(
        "JobPostingModel", back_populates="applications"
    )

    # Unique constraint for email + posting
    __table_args__ = (
        Index("ix_job_applications_job_posting_id", "job_posting_id"),
        Index("ix_job_applications_email_posting", "email", "job_posting_id"),
        Index("ix_job_applications_status", "status"),
        Index("ix_job_applications_is_read", "is_read"),
    )


class TurnoverITSkillModel(Base):
    """Cached Turnover-IT skill model."""

    __tablename__ = "turnoverit_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TurnoverITSkillsMetadataModel(Base):
    """Metadata for Turnover-IT skills sync."""

    __tablename__ = "turnoverit_skills_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_skills: Mapped[int] = mapped_column(Integer, default=0)


class AppSettingModel(Base):
    """Application runtime settings stored in database."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
