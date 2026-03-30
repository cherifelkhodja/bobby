"""Add purchase order requests table and clean contract requests.

Revision ID: 062
Revises: 061
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cm_purchase_order_requests (separate workflow for BDC) ──────────
    op.create_table(
        "cm_purchase_order_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "framework_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_framework_contracts.id"),
            nullable=False,
        ),
        sa.Column("boond_positioning_id", sa.Integer(), nullable=False),
        sa.Column("boond_candidate_id", sa.Integer(), nullable=True),
        sa.Column("boond_consultant_type", sa.String(20), nullable=True),
        sa.Column("boond_need_id", sa.Integer(), nullable=True),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=True,
        ),
        sa.Column("reference", sa.String(30), nullable=False, unique=True),
        sa.Column("commercial_email", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending_validation",
        ),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("quantity_sold", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("mission_title", sa.String(500), nullable=True),
        sa.Column("consultant_civility", sa.String(10), nullable=True),
        sa.Column("consultant_first_name", sa.String(255), nullable=True),
        sa.Column("consultant_last_name", sa.String(255), nullable=True),
        sa.Column("consultant_email", sa.String(255), nullable=True),
        sa.Column("consultant_phone", sa.String(50), nullable=True),
        sa.Column(
            "purchase_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_purchase_orders.id"),
            nullable=True,
        ),
        sa.Column(
            "original_contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=True,
        ),
        sa.Column("status_history", JSON(), nullable=True, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── Remove fast-path columns from cm_contract_requests ─────────────
    op.drop_column("cm_contract_requests", "framework_contract_id")
    op.drop_column("cm_contract_requests", "request_type")


def downgrade() -> None:
    # Re-add columns to cm_contract_requests
    op.add_column(
        "cm_contract_requests",
        sa.Column("request_type", sa.String(20), nullable=False, server_default="full"),
    )
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "framework_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_framework_contracts.id"),
            nullable=True,
        ),
    )
    op.drop_table("cm_purchase_order_requests")
