"""Add structured contact fields to tp_third_parties.

Représentant légal (split name + email + phone),
Signataire du contrat, Contact ADV, Contact facturation.

Revision ID: 030_tp_contact_fields
Revises: 029_tp_nullable_identity
Create Date: 2026-03-03
"""

import sqlalchemy as sa

from alembic import op

revision = "030_tp_contact_fields"
down_revision = "029_tp_nullable_identity"
branch_labels = None
depends_on = None

_COLS = [
    # Représentant légal (structured)
    ("representative_civility",      sa.String(10)),
    ("representative_first_name",    sa.String(100)),
    ("representative_last_name",     sa.String(100)),
    ("representative_email",         sa.String(255)),
    ("representative_phone",         sa.String(50)),
    # Signataire du contrat
    ("signatory_civility",           sa.String(10)),
    ("signatory_first_name",         sa.String(100)),
    ("signatory_last_name",          sa.String(100)),
    ("signatory_email",              sa.String(255)),
    ("signatory_phone",              sa.String(50)),
    # Contact ADV
    ("adv_contact_civility",         sa.String(10)),
    ("adv_contact_first_name",       sa.String(100)),
    ("adv_contact_last_name",        sa.String(100)),
    ("adv_contact_email",            sa.String(255)),
    ("adv_contact_phone",            sa.String(50)),
    # Contact facturation
    ("billing_contact_civility",     sa.String(10)),
    ("billing_contact_first_name",   sa.String(100)),
    ("billing_contact_last_name",    sa.String(100)),
    ("billing_contact_email",        sa.String(255)),
    ("billing_contact_phone",        sa.String(50)),
]


def upgrade() -> None:
    for col_name, col_type in _COLS:
        op.add_column(
            "tp_third_parties",
            sa.Column(col_name, col_type, nullable=True),
        )


def downgrade() -> None:
    for col_name, _ in reversed(_COLS):
        op.drop_column("tp_third_parties", col_name)
