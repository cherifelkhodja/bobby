"""Add reviewing_compliance status to contract requests.

New state in the contract lifecycle: ADV is reviewing documents
submitted by the third party before making a compliance decision.

Revision ID: 039
Revises: 038
Create Date: 2026-03-05
"""

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The status column is a plain VARCHAR — no enum type to alter.
    # The new value 'reviewing_compliance' is valid as-is once the
    # application code starts writing it.  This migration is a no-op
    # at the DB level but documents the state machine change.
    pass


def downgrade() -> None:
    # Reset any rows that have the new status back to collecting_documents
    # so a rollback does not leave orphaned states.
    op.execute(
        """
        UPDATE cm_contract_requests
        SET status = 'collecting_documents'
        WHERE status = 'reviewing_compliance'
        """
    )
