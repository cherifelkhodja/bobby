"""Add is_optional to cm_contract_article_templates and mark conditional articles as optional.

Revision ID: 050
Revises: 049
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None

# Articles that were previously hardcoded as conditional in compute_article_numbers()
OPTIONAL_ARTICLE_KEYS = [
    "confidentialite",
    "non_concurrence",
    "propriete_intellectuelle",
    "responsabilite",
    "mediation",
]


def upgrade() -> None:
    op.add_column(
        "cm_contract_article_templates",
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Mark pre-existing conditional articles as optional
    op.execute(
        f"""
        UPDATE cm_contract_article_templates
        SET is_optional = true
        WHERE article_key IN ({', '.join(f"'{k}'" for k in OPTIONAL_ARTICLE_KEYS)})
        """
    )


def downgrade() -> None:
    op.drop_column("cm_contract_article_templates", "is_optional")
