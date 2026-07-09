"""Make framework_contract_id nullable on purchase order requests.

A BDC (purchase order request) is now created directly from the positioning
webhook, potentially before the supplier's framework contract is signed. In
that locked state the BDC is not yet attached to any framework contract, so
the column must be nullable. It gets set when the BDC is unlocked (framework
contract signed).

Revision ID: 075
Revises: 074
"""

import sqlalchemy as sa

from alembic import op

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "cm_purchase_order_requests",
        "framework_contract_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "cm_purchase_order_requests",
        "framework_contract_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
