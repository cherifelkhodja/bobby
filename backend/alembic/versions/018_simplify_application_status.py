"""Simplify application status and add is_read field.

Revision ID: 018
Revises: 017
Create Date: 2025-01-21

Changes:
- Add is_read boolean field to track read/unread state (replaces nouveau/vu)
- Simplify statuses: en_cours, valide, refuse (remove nouveau, vu, entretien, accepte)
- Migrate existing data:
  - nouveau, vu → en_cours + is_read=False/True
  - entretien → en_cours
  - accepte → valide
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "018_simplify_application_status"
down_revision = "017_add_cv_quality_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_read field and simplify statuses."""
    # Add is_read column with default False
    op.add_column(
        "job_applications",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Create index for is_read
    op.create_index("ix_job_applications_is_read", "job_applications", ["is_read"])

    # Migrate existing data:
    # - nouveau → en_cours, is_read=False
    # - vu → en_cours, is_read=True
    # - entretien → en_cours (was in review, now just in_progress)
    # - accepte → valide
    # - en_cours stays en_cours
    # - refuse stays refuse

    # Set is_read=True for applications that were already viewed (vu status)
    op.execute("""
        UPDATE job_applications
        SET is_read = TRUE
        WHERE status IN ('vu', 'en_cours', 'entretien', 'accepte', 'refuse')
    """)

    # Convert statuses
    op.execute("""
        UPDATE job_applications
        SET status = 'en_cours'
        WHERE status IN ('nouveau', 'vu', 'entretien')
    """)

    op.execute("""
        UPDATE job_applications
        SET status = 'valide'
        WHERE status = 'accepte'
    """)


def downgrade() -> None:
    """Revert to old status system."""
    # Convert statuses back (best effort)
    op.execute("""
        UPDATE job_applications
        SET status = 'accepte'
        WHERE status = 'valide'
    """)

    op.execute("""
        UPDATE job_applications
        SET status = CASE
            WHEN is_read = FALSE THEN 'nouveau'
            ELSE 'vu'
        END
        WHERE status = 'en_cours'
    """)

    # Drop index and column
    op.drop_index("ix_job_applications_is_read", table_name="job_applications")
    op.drop_column("job_applications", "is_read")
