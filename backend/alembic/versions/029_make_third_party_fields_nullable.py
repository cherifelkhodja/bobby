"""Make ThirdParty identity fields nullable for stub creation workflow.

Revision ID: 029_tp_nullable_identity
Revises: 028_cr_consultant_address
Create Date: 2026-03-03
"""

import sqlalchemy as sa

from alembic import op

revision = "029_tp_nullable_identity"
down_revision = "028_cr_consultant_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make identity fields nullable so a stub ThirdParty can be created
    # with only contact_email + type at validate-commercial time.
    # The tiers will fill in the real data via the portal.
    op.alter_column("tp_third_parties", "company_name", nullable=True)
    op.alter_column("tp_third_parties", "legal_form", nullable=True)
    op.alter_column("tp_third_parties", "siren", nullable=True)
    op.alter_column("tp_third_parties", "siret", nullable=True)
    op.alter_column("tp_third_parties", "rcs_city", nullable=True)
    op.alter_column("tp_third_parties", "rcs_number", nullable=True)
    op.alter_column("tp_third_parties", "head_office_address", nullable=True)
    op.alter_column("tp_third_parties", "representative_name", nullable=True)
    op.alter_column("tp_third_parties", "representative_title", nullable=True)

    # Replace the global UNIQUE constraint on siren with a partial index
    # (only enforce uniqueness when siren is not null)
    op.drop_index("ix_tp_third_parties_siren", table_name="tp_third_parties")
    op.execute(
        "CREATE UNIQUE INDEX uq_tp_third_parties_siren_notnull "
        "ON tp_third_parties (siren) WHERE siren IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tp_third_parties_siren_notnull")
    op.create_index("ix_tp_third_parties_siren", "tp_third_parties", ["siren"], unique=True)

    op.alter_column("tp_third_parties", "representative_title", nullable=False)
    op.alter_column("tp_third_parties", "representative_name", nullable=False)
    op.alter_column("tp_third_parties", "head_office_address", nullable=False)
    op.alter_column("tp_third_parties", "rcs_number", nullable=False)
    op.alter_column("tp_third_parties", "rcs_city", nullable=False)
    op.alter_column("tp_third_parties", "siret", nullable=False)
    op.alter_column("tp_third_parties", "siren", nullable=False)
    op.alter_column("tp_third_parties", "legal_form", nullable=False)
    op.alter_column("tp_third_parties", "company_name", nullable=False)
