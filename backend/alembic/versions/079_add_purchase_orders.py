"""Add the purchase orders table (bons de commande).

Un bon de commande porte une mission d'un consultant chez un client, rattachée
à un fournisseur et à son contrat cadre. `third_party_id` et
`contract_request_id` sont nullables : un BDC créé par le webhook positionnement
naît sans fournisseur (« à rattacher »), l'ADV le complète ensuite.

Revision ID: 079
Revises: 078
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cm_purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reference",
            sa.String(20),
            nullable=False,
            unique=True,
            comment="Référence séquentielle du bon de commande (XXX-BC-NNN)",
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_companies.id"),
            nullable=True,
        ),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=True,
        ),
        sa.Column(
            "contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=True,
            comment="Contrat cadre de rattachement",
        ),
        sa.Column(
            "parent_purchase_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_purchase_orders.id"),
            nullable=True,
            comment="BDC d'origine en cas de reconduction",
        ),
        # Consultant
        sa.Column("boond_consultant_id", sa.Integer(), nullable=True),
        sa.Column("boond_consultant_type", sa.String(20), nullable=True),
        sa.Column("consultant_civility", sa.String(10), nullable=True),
        sa.Column("consultant_first_name", sa.String(255), nullable=True),
        sa.Column("consultant_last_name", sa.String(255), nullable=True),
        sa.Column("consultant_email", sa.String(255), nullable=True),
        sa.Column("consultant_phone", sa.String(50), nullable=True),
        # Origine Boond
        sa.Column("boond_positioning_id", sa.Integer(), nullable=True),
        sa.Column("boond_need_id", sa.Integer(), nullable=True),
        sa.Column(
            "boond_delivery_id",
            sa.Integer(),
            nullable=True,
            comment="Prestation Boond, support du renouvellement (POST /deliveries/{id}/renew)",
        ),
        # Mission
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("mission_title", sa.String(500), nullable=True),
        sa.Column("mission_description", sa.Text(), nullable=True),
        sa.Column("mission_site_name", sa.String(255), nullable=True),
        sa.Column("mission_address", sa.String(500), nullable=True),
        sa.Column("mission_postal_code", sa.String(10), nullable=True),
        sa.Column("mission_city", sa.String(255), nullable=True),
        # Conditions financières
        sa.Column(
            "sale_daily_rate",
            sa.Numeric(10, 2),
            nullable=True,
            comment="TJM de vente client — interne, jamais imprimé sur le document fournisseur",
        ),
        sa.Column(
            "purchase_daily_rate",
            sa.Numeric(10, 2),
            nullable=True,
            comment="CJM d'achat fournisseur — le seul taux du bon de commande",
        ),
        sa.Column("days_sold", sa.Numeric(6, 2), nullable=True),
        sa.Column("free_days", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        # Documents et signature
        sa.Column("s3_key_draft", sa.String(500), nullable=True),
        sa.Column("s3_key_signed", sa.String(500), nullable=True),
        sa.Column("yousign_envelope_id", sa.String(100), nullable=True),
        sa.Column("sent_for_signature_at", sa.DateTime(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        # Synchronisation Boond
        sa.Column("boond_contract_id", sa.Integer(), nullable=True),
        sa.Column("boond_purchase_order_id", sa.Integer(), nullable=True),
        sa.Column("boond_sync_error", sa.Text(), nullable=True),
        sa.Column("commercial_email", sa.String(255), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status_history", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_cm_purchase_orders_third_party",
        "cm_purchase_orders",
        ["third_party_id"],
    )
    op.create_index(
        "ix_cm_purchase_orders_contract_request",
        "cm_purchase_orders",
        ["contract_request_id"],
    )
    op.create_index(
        "ix_cm_purchase_orders_status",
        "cm_purchase_orders",
        ["status"],
    )

    # Un seul BDC d'origine vivant par positionnement : le webhook est ainsi
    # idempotent. Les reconductions (parent_purchase_order_id renseigné)
    # reprennent le même positionnement et sont hors de la contrainte, comme
    # les BDC annulés — qui libèrent le positionnement pour une recréation.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cm_purchase_orders_boond_positioning
        ON cm_purchase_orders (boond_positioning_id)
        WHERE boond_positioning_id IS NOT NULL
          AND parent_purchase_order_id IS NULL
          AND status != 'cancelled'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cm_purchase_orders_boond_positioning")
    op.drop_index("ix_cm_purchase_orders_status", table_name="cm_purchase_orders")
    op.drop_index("ix_cm_purchase_orders_contract_request", table_name="cm_purchase_orders")
    op.drop_index("ix_cm_purchase_orders_third_party", table_name="cm_purchase_orders")
    op.drop_table("cm_purchase_orders")
