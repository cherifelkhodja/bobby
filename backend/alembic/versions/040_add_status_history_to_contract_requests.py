"""Add status_history column to cm_contract_requests.

Stores the ordered list of status transitions:
[{"status": "collecting_documents", "entered_at": "2026-03-05T10:05:00"}, ...]

Revision ID: 040
Revises: 039
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_requests",
        sa.Column("status_history", sa.JSON(), nullable=True),
    )
    # Initialise existing rows with an empty list
    op.execute("UPDATE cm_contract_requests SET status_history = '[]'::jsonb WHERE status_history IS NULL")


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "status_history")
