"""Add signature uploads table.

Revision ID: 071
Revises: 070
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cm_signature_uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contract_request_id", UUID(as_uuid=True), sa.ForeignKey("cm_contract_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charter_template_id", UUID(as_uuid=True), sa.ForeignKey("cm_charter_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_kind", sa.String(30), nullable=False, comment="contract, charter_ar, charter_engagement"),
        sa.Column("signer_role", sa.String(20), nullable=False, comment="partner or consultant"),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_cm_signature_uploads_cr_id", "cm_signature_uploads", ["contract_request_id"])


def downgrade() -> None:
    op.drop_index("ix_cm_signature_uploads_cr_id", table_name="cm_signature_uploads")
    op.drop_table("cm_signature_uploads")
