"""Drop BDC module tables (purchase orders, purchase order requests, framework contracts).

The BDC module has been removed from the codebase. This migration drops its
tables in FK-dependency order.

Revision ID: 077
Revises: 076
"""

from alembic import op

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop in FK-dependency order (children first).
    op.execute("DROP TABLE IF EXISTS cm_purchase_order_requests CASCADE")
    op.execute("DROP TABLE IF EXISTS cm_purchase_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS cm_framework_contracts CASCADE")


def downgrade() -> None:
    # Irreversible: the BDC module was removed. Recreating the tables would
    # require restoring the removed models — out of scope for a downgrade.
    raise NotImplementedError("BDC module removal is not reversible.")
