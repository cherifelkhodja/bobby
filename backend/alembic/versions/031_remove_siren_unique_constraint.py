"""Remove unique constraint on SIREN for tp_third_parties.

Un même SIREN peut être associé à plusieurs tiers (plusieurs contrats
pour une même entreprise).

Revision ID: 031_remove_siren_unique
Revises: 030_tp_contact_fields
Create Date: 2026-03-04
"""

from alembic import op

revision = "031_remove_siren_unique"
down_revision = "030_tp_contact_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_tp_third_parties_siren", table_name="tp_third_parties")
    op.create_index("ix_tp_third_parties_siren", "tp_third_parties", ["siren"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tp_third_parties_siren", table_name="tp_third_parties")
    op.create_index("ix_tp_third_parties_siren", "tp_third_parties", ["siren"], unique=True)
