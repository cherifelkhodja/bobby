"""Replace unique constraint on boond_positioning_id with partial unique index.

Revision ID: 026_partial_uniq_pos
Revises: 025_contract_vigil
Create Date: 2026-02-15

Allows re-creating a contract request for the same positioning after
cancellation. The unique constraint now only applies to non-cancelled CRs.
"""

from alembic import op

revision = "026_partial_uniq_pos"
down_revision = "025_contract_vigil"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old absolute unique index
    op.drop_index(
        "uq_cm_contract_requests_boond_positioning",
        table_name="cm_contract_requests",
    )

    # Create a partial unique index: unique only when status != 'cancelled'
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cm_contract_requests_boond_positioning
        ON cm_contract_requests (boond_positioning_id)
        WHERE status != 'cancelled'
        """
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cm_contract_requests_boond_positioning",
        table_name="cm_contract_requests",
    )
    op.create_index(
        "uq_cm_contract_requests_boond_positioning",
        "cm_contract_requests",
        ["boond_positioning_id"],
        unique=True,
    )
