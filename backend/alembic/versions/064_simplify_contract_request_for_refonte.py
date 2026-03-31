"""Simplify contract requests for ADR-009 refonte.

Add trigger_type and previous_contract_request_id columns.
Make boond_positioning_id nullable (new webhooks don't have positioning).

Revision ID: 064
Revises: 063
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trigger_type: what triggered this contract request
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "trigger_type",
            sa.String(30),
            nullable=True,
            comment="What triggered this CR: positioning_7, candidat_11, ressource_4, ressource_5",
        ),
    )

    # Add previous_contract_request_id for re-contractualization (state 4/5)
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "previous_contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=True,
            comment="Link to previous CR for re-contractualization",
        ),
    )

    # Add boond_resource_id: for resource-triggered workflows (states 4/5)
    op.add_column(
        "cm_contract_requests",
        sa.Column(
            "boond_resource_id",
            sa.Integer(),
            nullable=True,
            comment="Boond resource ID for resource-triggered workflows",
        ),
    )

    # Make boond_positioning_id nullable: new webhooks (candidate/resource)
    # don't have a positioning ID
    op.alter_column(
        "cm_contract_requests",
        "boond_positioning_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Make commercial_email nullable: may not be known at creation for new triggers
    op.alter_column(
        "cm_contract_requests",
        "commercial_email",
        existing_type=sa.String(255),
        nullable=True,
    )

    # Backfill existing rows with trigger_type = 'positioning_7'
    op.execute(
        "UPDATE cm_contract_requests SET trigger_type = 'positioning_7' WHERE trigger_type IS NULL"
    )


def downgrade() -> None:
    # Restore NOT NULL on commercial_email (set empty string for nulls first)
    op.execute(
        "UPDATE cm_contract_requests SET commercial_email = '' WHERE commercial_email IS NULL"
    )
    op.alter_column(
        "cm_contract_requests",
        "commercial_email",
        existing_type=sa.String(255),
        nullable=False,
    )

    # Restore NOT NULL on boond_positioning_id (set 0 for nulls first)
    op.execute(
        "UPDATE cm_contract_requests SET boond_positioning_id = 0 WHERE boond_positioning_id IS NULL"
    )
    op.alter_column(
        "cm_contract_requests",
        "boond_positioning_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column("cm_contract_requests", "boond_resource_id")
    op.drop_column("cm_contract_requests", "previous_contract_request_id")
    op.drop_column("cm_contract_requests", "trigger_type")
