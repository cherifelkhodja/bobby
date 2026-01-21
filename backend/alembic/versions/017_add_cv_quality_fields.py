"""Add CV quality evaluation fields to job_applications table.

Revision ID: 017
Revises: 016
Create Date: 2025-01-21

New fields for CV quality evaluation (/20):
- cv_quality_score: Float (0-20) - Global CV quality score
- cv_quality: JSON - Detailed evaluation with breakdown by category
  - niveau_experience: JUNIOR/CONFIRME/SENIOR
  - annees_experience: Float
  - details_notes: stability, account quality, education, continuity, bonus/malus
  - points_forts, points_faibles, synthese, classification
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "017_add_cv_quality_fields"
down_revision = "016_add_application_form_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add CV quality evaluation fields to job_applications table."""
    op.add_column(
        "job_applications",
        sa.Column("cv_quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("cv_quality", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Remove CV quality evaluation fields from job_applications table."""
    op.drop_column("job_applications", "cv_quality")
    op.drop_column("job_applications", "cv_quality_score")
