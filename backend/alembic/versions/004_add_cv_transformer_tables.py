"""Add CV transformer tables (cv_templates, cv_transformation_logs)

Revision ID: 004_add_cv_transformer_tables
Revises: 003_add_inv_boond_ids
Create Date: 2026-01-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_cv_transformer_tables"
down_revision: str | None = "003_add_inv_boond_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create cv_templates table
    op.create_table(
        "cv_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("file_content", sa.LargeBinary, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Create cv_transformation_logs table
    op.create_table(
        "cv_transformation_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "template_id", UUID(as_uuid=True), sa.ForeignKey("cv_templates.id"), nullable=True
        ),
        sa.Column("template_name", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # Create index on user_id for faster stats queries
    op.create_index("ix_cv_transformation_logs_user_id", "cv_transformation_logs", ["user_id"])
    op.create_index(
        "ix_cv_transformation_logs_created_at", "cv_transformation_logs", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_cv_transformation_logs_created_at", table_name="cv_transformation_logs")
    op.drop_index("ix_cv_transformation_logs_user_id", table_name="cv_transformation_logs")
    op.drop_table("cv_transformation_logs")
    op.drop_table("cv_templates")
