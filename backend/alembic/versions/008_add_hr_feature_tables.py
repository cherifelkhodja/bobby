"""Add HR feature tables (job_postings, job_applications).

Revision ID: 008_add_hr_feature_tables
Revises: 007_add_quotation_templates_table
Create Date: 2026-01-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = "008_add_hr_feature_tables"
down_revision = "007_add_quotation_templates_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create job_postings and job_applications tables."""
    # Create job_postings table
    op.create_table(
        "job_postings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("qualifications", sa.Text, nullable=False),
        sa.Column("location_country", sa.String(50), nullable=False),
        sa.Column("location_region", sa.String(100), nullable=True),
        sa.Column("location_postal_code", sa.String(20), nullable=True),
        sa.Column("location_city", sa.String(100), nullable=True),
        sa.Column("contract_types", JSON, nullable=False, server_default="[]"),
        sa.Column("skills", JSON, nullable=True, server_default="[]"),
        sa.Column("experience_level", sa.String(50), nullable=True),
        sa.Column("remote", sa.String(20), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("duration_months", sa.Integer, nullable=True),
        sa.Column("salary_min_annual", sa.Float, nullable=True),
        sa.Column("salary_max_annual", sa.Float, nullable=True),
        sa.Column("salary_min_daily", sa.Float, nullable=True),
        sa.Column("salary_max_daily", sa.Float, nullable=True),
        sa.Column("employer_overview", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("turnoverit_reference", sa.String(100), nullable=True, unique=True),
        sa.Column("turnoverit_public_url", sa.String(500), nullable=True),
        sa.Column("application_token", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("closed_at", sa.DateTime, nullable=True),
    )

    # Indexes for job_postings
    op.create_index(
        "ix_job_postings_opportunity_id", "job_postings", ["opportunity_id"]
    )
    op.create_index(
        "ix_job_postings_application_token", "job_postings", ["application_token"]
    )
    op.create_index("ix_job_postings_status", "job_postings", ["status"])
    op.create_index("ix_job_postings_created_by", "job_postings", ["created_by"])
    op.create_index(
        "ix_job_postings_turnoverit_reference", "job_postings", ["turnoverit_reference"]
    )

    # Create job_applications table
    op.create_table(
        "job_applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_posting_id",
            UUID(as_uuid=True),
            sa.ForeignKey("job_postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("job_title", sa.String(200), nullable=False),
        sa.Column("tjm_min", sa.Float, nullable=False),
        sa.Column("tjm_max", sa.Float, nullable=False),
        sa.Column("availability_date", sa.Date, nullable=False),
        sa.Column("cv_s3_key", sa.String(500), nullable=False),
        sa.Column("cv_filename", sa.String(255), nullable=False),
        sa.Column("cv_text", sa.Text, nullable=True),
        sa.Column("matching_score", sa.Integer, nullable=True),
        sa.Column("matching_details", JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="nouveau"),
        sa.Column("status_history", JSON, nullable=True, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("boond_candidate_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Indexes for job_applications
    op.create_index(
        "ix_job_applications_job_posting_id", "job_applications", ["job_posting_id"]
    )
    op.create_index("ix_job_applications_status", "job_applications", ["status"])
    op.create_index(
        "ix_job_applications_matching_score", "job_applications", ["matching_score"]
    )
    op.create_index("ix_job_applications_email", "job_applications", ["email"])
    op.create_index(
        "ix_job_applications_created_at", "job_applications", ["created_at"]
    )


def downgrade() -> None:
    """Drop job_applications and job_postings tables."""
    # Drop indexes for job_applications
    op.drop_index("ix_job_applications_created_at", table_name="job_applications")
    op.drop_index("ix_job_applications_email", table_name="job_applications")
    op.drop_index("ix_job_applications_matching_score", table_name="job_applications")
    op.drop_index("ix_job_applications_status", table_name="job_applications")
    op.drop_index("ix_job_applications_job_posting_id", table_name="job_applications")

    # Drop job_applications table
    op.drop_table("job_applications")

    # Drop indexes for job_postings
    op.drop_index("ix_job_postings_turnoverit_reference", table_name="job_postings")
    op.drop_index("ix_job_postings_created_by", table_name="job_postings")
    op.drop_index("ix_job_postings_status", table_name="job_postings")
    op.drop_index("ix_job_postings_application_token", table_name="job_postings")
    op.drop_index("ix_job_postings_opportunity_id", table_name="job_postings")

    # Drop job_postings table
    op.drop_table("job_postings")
