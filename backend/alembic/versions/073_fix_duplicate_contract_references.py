"""Data fix: reset GEM-CC-002 and CRA-CC-002 references back to -001.

Revision ID: 073
Revises: 072
"""

import sqlalchemy as sa

from alembic import op

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete contract documents with the -002 references
    op.execute(sa.text("""
        DELETE FROM cm_contracts
        WHERE reference IN ('GEM-CC-002', 'CRA-CC-002')
    """))

    # Delete framework contracts with the -002 references
    op.execute(sa.text("""
        DELETE FROM cm_framework_contracts
        WHERE reference IN ('GEM-CC-002', 'CRA-CC-002')
    """))

    # Reset contract request references from -002 to -001
    op.execute(sa.text("""
        UPDATE cm_contract_requests
        SET reference = 'GEM-CC-001'
        WHERE reference = 'GEM-CC-002'
    """))

    op.execute(sa.text("""
        UPDATE cm_contract_requests
        SET reference = 'CRA-CC-001'
        WHERE reference = 'CRA-CC-002'
    """))

    # Fix: restore archived CRs that should be active
    op.execute(sa.text("""
        UPDATE cm_contract_requests
        SET status = 'active',
            status_history = status_history || '[{"status": "active", "entered_at": "' || now()::text || '"}]'::jsonb
        WHERE reference IN ('GEM-CC-001')
        AND status = 'archived'
    """))


def downgrade() -> None:
    # No safe downgrade for data fixes
    pass
