"""Add framework contracts, purchase orders tables and request_type to contract requests.

Revision ID: 061
Revises: 060
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cm_framework_contracts ─────────────────────────────────────────────
    op.create_table(
        "cm_framework_contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_companies.id"),
            nullable=False,
        ),
        sa.Column(
            "original_contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "original_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contracts.id"),
            nullable=True,
        ),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("s3_key_signed", sa.String(500), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("tacit_renewal", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    # One active framework contract per (third_party, company) pair
    op.create_index(
        "ix_cm_framework_contracts_tp_company_active",
        "cm_framework_contracts",
        ["third_party_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # ── cm_purchase_orders ─────────────────────────────────────────────────
    op.create_table(
        "cm_purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "framework_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_framework_contracts.id"),
            nullable=False,
        ),
        sa.Column(
            "contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(30), nullable=False, unique=True),
        sa.Column("consultant_first_name", sa.String(255), nullable=True),
        sa.Column("consultant_last_name", sa.String(255), nullable=True),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("boond_positioning_id", sa.Integer(), nullable=False),
        sa.Column("boond_purchase_order_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── Alter cm_contract_requests ─────────────────────────────────────────
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "request_type",
            sa.String(20),
            nullable=False,
            server_default="full",
        ),
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


def downgrade() -> None:
    op.drop_column("cm_contract_requests", "framework_contract_id")
    op.drop_column("cm_contract_requests", "request_type")
    op.drop_table("cm_purchase_orders")
    op.drop_index(
        "ix_cm_framework_contracts_tp_company_active",
        table_name="cm_framework_contracts",
    )
    op.drop_table("cm_framework_contracts")
