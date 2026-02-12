"""Reset all job applications to en_cours for Boond re-validation.

Revision ID: 020_reset_apps_revalidation
Revises: 019_add_civility_and_boond_sync
Create Date: 2026-02-11

One-time data migration:
- Reset status to 'en_cours' for all applications
- Reset is_read to false
- Clear boond_candidate_id, boond_sync_error, boond_synced_at
  so auto-sync triggers again on next validation
- Clear status_history (fresh start)
"""

import sqlalchemy as sa

from alembic import op

revision = "020_reset_apps_revalidation"
down_revision = "019_add_civility_and_boond_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE job_applications
            SET status = 'en_cours',
                is_read = false,
                boond_candidate_id = NULL,
                boond_sync_error = NULL,
                boond_synced_at = NULL,
                status_history = '[]'::jsonb,
                updated_at = NOW()
        """)
    )


def downgrade() -> None:
    # Data migration — cannot be reversed automatically
    pass
