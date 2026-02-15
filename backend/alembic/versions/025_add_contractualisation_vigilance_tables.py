"""Add contractualisation and vigilance documentaire tables.

Revision ID: 025_contract_vigil
Revises: 024_reset_opps_coopts
Create Date: 2026-02-15

Creates 6 tables for the 3 new bounded contexts:
- tp_third_parties: Third party (freelance / subcontractor) registry
- tp_magic_links: Secure portal access tokens
- vig_documents: Vigilance document lifecycle
- cm_contract_requests: Contract request workflow
- cm_contracts: Generated and signed contracts
- cm_webhook_events: Idempotent webhook event log

Also adds RLS policies on vig_documents and cm_contract_requests.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = "025_contract_vigil"
down_revision = "024_reset_opps_coopts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tp_third_parties ─────────────────────────────────────────
    op.create_table(
        "tp_third_parties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("boond_provider_id", sa.Integer, nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("legal_form", sa.String(100), nullable=False),
        sa.Column("capital", sa.String(50), nullable=True),
        sa.Column("siren", sa.String(9), nullable=False),
        sa.Column("siret", sa.String(14), nullable=False),
        sa.Column("rcs_city", sa.String(100), nullable=False),
        sa.Column("rcs_number", sa.String(50), nullable=False),
        sa.Column("head_office_address", sa.Text, nullable=False),
        sa.Column("representative_name", sa.String(255), nullable=False),
        sa.Column("representative_title", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column(
            "compliance_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_tp_third_parties_siren", "tp_third_parties", ["siren"], unique=True)

    # ── cm_contract_requests (before tp_magic_links due to FK) ───
    op.create_table(
        "cm_contract_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("boond_positioning_id", sa.Integer, nullable=False),
        sa.Column("boond_candidate_id", sa.Integer, nullable=True),
        sa.Column("boond_need_id", sa.Integer, nullable=True),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending_commercial_validation",
        ),
        sa.Column("third_party_type", sa.String(20), nullable=True),
        sa.Column("daily_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("mission_description", sa.Text, nullable=True),
        sa.Column("mission_location", sa.Text, nullable=True),
        sa.Column("contractualization_contact_email", sa.String(255), nullable=True),
        sa.Column("contract_config", JSON, nullable=True),
        sa.Column("commercial_email", sa.String(255), nullable=False),
        sa.Column("commercial_validated_at", sa.DateTime, nullable=True),
        sa.Column(
            "compliance_override",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("compliance_override_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_cm_contract_requests_boond_positioning",
        "cm_contract_requests",
        ["boond_positioning_id"],
        unique=True,
    )
    op.create_index(
        "ix_cm_contract_requests_status",
        "cm_contract_requests",
        ["status"],
    )

    # ── tp_magic_links ───────────────────────────────────────────
    op.create_table(
        "tp_magic_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=False,
        ),
        sa.Column(
            "contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=True,
        ),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("email_sent_to", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("accessed_at", sa.DateTime, nullable=True),
        sa.Column(
            "is_revoked",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_tp_magic_links_token", "tp_magic_links", ["token"], unique=True)

    # ── vig_documents ────────────────────────────────────────────
    op.create_table(
        "vig_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="requested",
        ),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("uploaded_at", sa.DateTime, nullable=True),
        sa.Column("validated_at", sa.DateTime, nullable=True),
        sa.Column("validated_by", sa.String(255), nullable=True),
        sa.Column("rejected_at", sa.DateTime, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("auto_check_results", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_vig_documents_third_party_id",
        "vig_documents",
        ["third_party_id"],
    )
    op.create_index("ix_vig_documents_status", "vig_documents", ["status"])
    op.create_index("ix_vig_documents_expires_at", "vig_documents", ["expires_at"])

    # ── cm_contracts ─────────────────────────────────────────────
    op.create_table(
        "cm_contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cm_contract_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "third_party_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tp_third_parties.id"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("s3_key_draft", sa.String(500), nullable=False),
        sa.Column("s3_key_signed", sa.String(500), nullable=True),
        sa.Column("yousign_procedure_id", sa.String(100), nullable=True),
        sa.Column("yousign_status", sa.String(50), nullable=True),
        sa.Column("boond_purchase_order_id", sa.Integer, nullable=True),
        sa.Column("partner_comments", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("signed_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_cm_contracts_contract_request_id",
        "cm_contracts",
        ["contract_request_id"],
    )

    # ── cm_webhook_events ────────────────────────────────────────
    op.create_table(
        "cm_webhook_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", JSON, nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── RLS Policies ─────────────────────────────────────────────
    # Following existing pattern from migration 010

    # RLS on vig_documents: ADV and admin see all
    op.execute("ALTER TABLE vig_documents ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS vig_documents_select_policy ON vig_documents;")
    op.execute("""
        CREATE POLICY vig_documents_select_policy ON vig_documents
            FOR SELECT
            USING (
                current_setting('app.user_role', true) IN ('admin', 'adv')
            );
    """)
    op.execute("DROP POLICY IF EXISTS vig_documents_all_policy ON vig_documents;")
    op.execute("""
        CREATE POLICY vig_documents_all_policy ON vig_documents
            FOR ALL
            USING (
                current_setting('app.user_role', true) IN ('admin', 'adv')
            );
    """)
    # Allow public insert (portal upload via magic link)
    op.execute("DROP POLICY IF EXISTS vig_documents_insert_policy ON vig_documents;")
    op.execute("""
        CREATE POLICY vig_documents_insert_policy ON vig_documents
            FOR INSERT
            WITH CHECK (true);
    """)

    # RLS on cm_contract_requests: ADV and admin see all, commercial sees own
    op.execute("ALTER TABLE cm_contract_requests ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS cm_contract_requests_select_policy ON cm_contract_requests;"
    )
    op.execute("""
        CREATE POLICY cm_contract_requests_select_policy ON cm_contract_requests
            FOR SELECT
            USING (
                current_setting('app.user_role', true) IN ('admin', 'adv')
                OR commercial_email = current_setting('app.user_email', true)
            );
    """)
    op.execute(
        "DROP POLICY IF EXISTS cm_contract_requests_all_policy ON cm_contract_requests;"
    )
    op.execute("""
        CREATE POLICY cm_contract_requests_all_policy ON cm_contract_requests
            FOR ALL
            USING (
                current_setting('app.user_role', true) IN ('admin', 'adv')
            );
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS cm_contract_requests_all_policy ON cm_contract_requests;")
    op.execute(
        "DROP POLICY IF EXISTS cm_contract_requests_select_policy ON cm_contract_requests;"
    )
    op.execute("ALTER TABLE cm_contract_requests DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS vig_documents_insert_policy ON vig_documents;")
    op.execute("DROP POLICY IF EXISTS vig_documents_all_policy ON vig_documents;")
    op.execute("DROP POLICY IF EXISTS vig_documents_select_policy ON vig_documents;")
    op.execute("ALTER TABLE vig_documents DISABLE ROW LEVEL SECURITY;")

    # Drop tables in reverse order (respecting FK constraints)
    op.drop_table("cm_webhook_events")
    op.drop_table("cm_contracts")
    op.drop_table("vig_documents")
    op.drop_table("tp_magic_links")
    op.drop_table("cm_contract_requests")
    op.drop_table("tp_third_parties")
