"""Placeholder migration for database compatibility.

Revision ID: 008_add_published_opportunities
Revises: 007_add_quotation_templates
Create Date: 2026-01-15

Note: This is a placeholder migration to maintain compatibility with
databases that already have this revision applied.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "008_add_published_opportunities"
down_revision: Union[str, None] = "007_add_quotation_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: placeholder for compatibility."""
    pass


def downgrade() -> None:
    """No-op: placeholder for compatibility."""
    pass
