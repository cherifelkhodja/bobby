"""Make contract_request_id nullable on purchase orders.

A BDC (purchase order) created from the positioning webhook has no originating
ContractRequest, so cm_purchase_orders.contract_request_id must be nullable
(it was NOT NULL with a FK to cm_contract_requests, causing a FK violation on
finalize).

Revision ID: 076
Revises: 075
"""

import sqlalchemy as sa

from alembic import op

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "cm_purchase_orders",
        "contract_request_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "cm_purchase_orders",
        "contract_request_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
