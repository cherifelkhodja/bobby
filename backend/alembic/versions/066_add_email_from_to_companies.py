"""Add email_from to cm_contract_companies.

Revision ID: 066
Revises: 065
"""

import sqlalchemy as sa

from alembic import op

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cm_contract_companies",
        sa.Column(
            "email_from",
            sa.String(255),
            nullable=True,
            comment="Email expediteur pour les mails lies a cette societe",
        ),
    )


def downgrade() -> None:
    op.drop_column("cm_contract_companies", "email_from")
