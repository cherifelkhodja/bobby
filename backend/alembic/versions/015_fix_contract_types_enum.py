"""Fix contract_types enum values for Turnover-IT compatibility.

Revision ID: 015_fix_contract_types_enum
Revises: 014_add_location_key
Create Date: 2026-01-21

Turnover-IT API only accepts these contract types:
- PERMANENT (CDI)
- FIXED-TERM (CDD)
- FREELANCE

This migration:
- Replaces TEMPORARY with FIXED-TERM
- Removes invalid values: INTERNSHIP, APPRENTICESHIP, INTERCONTRACT
"""

from alembic import op


# revision identifiers
revision = "015_fix_contract_types_enum"
down_revision = "014_add_location_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix contract_types values in job_postings table."""
    # Use raw SQL to update JSON array
    # 1. Replace TEMPORARY with FIXED-TERM (if FIXED-TERM not already present)
    # 2. Remove invalid values: TEMPORARY, INTERNSHIP, APPRENTICESHIP, INTERCONTRACT

    op.execute("""
        UPDATE job_postings
        SET contract_types = (
            SELECT jsonb_agg(DISTINCT
                CASE
                    WHEN elem = 'TEMPORARY' THEN 'FIXED-TERM'
                    ELSE elem
                END
            )
            FROM jsonb_array_elements_text(contract_types::jsonb) AS elem
            WHERE elem NOT IN ('TEMPORARY', 'INTERNSHIP', 'APPRENTICESHIP', 'INTERCONTRACT')
        )::json
        WHERE contract_types::text LIKE '%TEMPORARY%'
           OR contract_types::text LIKE '%INTERNSHIP%'
           OR contract_types::text LIKE '%APPRENTICESHIP%'
           OR contract_types::text LIKE '%INTERCONTRACT%';
    """)


def downgrade() -> None:
    """Revert contract_types changes (best effort - data may be lost)."""
    # Note: This is a lossy operation - we can't know which FIXED-TERM were originally TEMPORARY
    pass
