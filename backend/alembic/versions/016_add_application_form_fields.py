"""Add new fields to job_applications table.

Revision ID: 016
Revises: 015
Create Date: 2025-01-21

New fields:
- availability: Dropdown instead of date (asap, 1_month, 2_months, 3_months, more_3_months)
- employment_status: freelance, employee, both
- english_level: notions, intermediate, professional, fluent, bilingual
- tjm_current, tjm_desired: For freelance
- salary_current, salary_desired: For employee

Legacy fields (tjm_min, tjm_max, availability_date) are made nullable for backward compatibility.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "016_add_application_form_fields"
down_revision = "015_fix_contract_types_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new fields to job_applications table."""
    # Add new fields
    op.add_column(
        "job_applications",
        sa.Column("availability", sa.String(50), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("employment_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("english_level", sa.String(20), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("tjm_current", sa.Float(), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("tjm_desired", sa.Float(), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("salary_current", sa.Float(), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("salary_desired", sa.Float(), nullable=True),
    )

    # Make legacy fields nullable
    op.alter_column(
        "job_applications",
        "tjm_min",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "job_applications",
        "tjm_max",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "job_applications",
        "availability_date",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove new fields from job_applications table."""
    # Remove new fields
    op.drop_column("job_applications", "availability")
    op.drop_column("job_applications", "employment_status")
    op.drop_column("job_applications", "english_level")
    op.drop_column("job_applications", "tjm_current")
    op.drop_column("job_applications", "tjm_desired")
    op.drop_column("job_applications", "salary_current")
    op.drop_column("job_applications", "salary_desired")

    # Restore legacy fields as not nullable (may fail if data exists)
    op.alter_column(
        "job_applications",
        "tjm_min",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column(
        "job_applications",
        "tjm_max",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column(
        "job_applications",
        "availability_date",
        existing_type=sa.Date(),
        nullable=False,
    )
