"""Remove unique constraint on SIREN for tp_third_parties.

Un même SIREN peut être associé à plusieurs tiers (plusieurs contrats
pour une même entreprise).

Revision ID: 031_remove_siren_unique
Revises: 030_tp_contact_fields
Create Date: 2026-03-04
"""

from alembic import op
from sqlalchemy import text

revision = "031_remove_siren_unique"
down_revision = "030_tp_contact_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any unique index or constraint on siren, regardless of name
    op.execute(text("""
        DO $$
        DECLARE
            idx_name TEXT;
        BEGIN
            -- Drop unique indexes on siren column
            FOR idx_name IN
                SELECT i.relname
                FROM pg_index ix
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relname = 'tp_third_parties'
                  AND a.attname = 'siren'
                  AND ix.indisunique = true
            LOOP
                EXECUTE format('DROP INDEX IF EXISTS %I', idx_name);
            END LOOP;

            -- Drop unique constraints on siren column
            FOR idx_name IN
                SELECT c.conname
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
                WHERE t.relname = 'tp_third_parties'
                  AND a.attname = 'siren'
                  AND c.contype = 'u'
            LOOP
                EXECUTE format('ALTER TABLE tp_third_parties DROP CONSTRAINT IF EXISTS %I', idx_name);
            END LOOP;
        END $$;
    """))

    # Create a non-unique index for query performance
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_tp_third_parties_siren ON tp_third_parties (siren)
    """))


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS ix_tp_third_parties_siren"))
    op.execute(text("""
        CREATE UNIQUE INDEX ix_tp_third_parties_siren ON tp_third_parties (siren)
    """))
