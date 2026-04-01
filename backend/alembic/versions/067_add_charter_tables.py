"""Add charter templates and acknowledgements tables.

Revision ID: 067
Revises: 066
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Charter templates (uploaded by admin)
    op.create_table(
        "cm_charter_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("target", sa.String(20), nullable=False, comment="partner or consultant"),
        sa.Column("file_s3_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Charter acknowledgements (signed/accepted by partners or consultants)
    op.create_table(
        "cm_charter_acknowledgements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("charter_template_id", UUID(as_uuid=True), sa.ForeignKey("cm_charter_templates.id"), nullable=False),
        sa.Column("third_party_id", UUID(as_uuid=True), sa.ForeignKey("tp_third_parties.id"), nullable=True),
        sa.Column("contract_request_id", UUID(as_uuid=True), sa.ForeignKey("cm_contract_requests.id"), nullable=True),
        sa.Column("consultant_name", sa.String(255), nullable=True, comment="Null for partner acknowledgements"),
        sa.Column("consultant_email", sa.String(255), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("method", sa.String(20), nullable=False, server_default=sa.text("'checkbox'"), comment="checkbox or yousign"),
        sa.Column("yousign_envelope_id", sa.String(100), nullable=True),
        sa.Column("signed_document_s3_key", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Contract consultants (for tracking per-consultant charter status)
    op.create_table(
        "cm_contract_consultants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contract_request_id", UUID(as_uuid=True), sa.ForeignKey("cm_contract_requests.id"), nullable=False),
        sa.Column("boond_candidate_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("charter_status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), comment="pending, sent, signed"),
        sa.Column("yousign_envelope_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("cm_contract_consultants")
    op.drop_table("cm_charter_acknowledgements")
    op.drop_table("cm_charter_templates")
