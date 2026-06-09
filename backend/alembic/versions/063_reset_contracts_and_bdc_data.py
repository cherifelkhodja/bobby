"""Reset all contract and BDC data (clean slate).

Revision ID: 063
Revises: 062
Create Date: 2026-03-31

One-time data migration: clear all contract management operational data.
Preserves configuration tables: article templates, annex templates, contract companies.
Also purges S3 contract files (prefix: contracts/).
"""

import asyncio
import logging

import sqlalchemy as sa

from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def _purge_s3_contracts() -> None:
    """Best-effort S3 cleanup of contract PDFs."""
    try:
        from app.config import get_settings
        from app.infrastructure.storage.s3_client import S3StorageClient

        settings = get_settings()
        s3 = S3StorageClient(settings)
        deleted = asyncio.get_event_loop().run_until_complete(s3.delete_prefix("contracts/"))
        logger.info(f"S3 cleanup: deleted {deleted} contract files")
    except Exception as exc:
        logger.warning(f"S3 cleanup skipped (non-blocking): {exc}")


def upgrade() -> None:
    # Order matters — respect foreign key dependencies (children first)

    # 1. Purchase order requests (FK → framework_contracts, purchase_orders, contract_requests)
    op.execute(sa.text("DELETE FROM cm_purchase_order_requests"))

    # 2. Purchase orders (FK → framework_contracts, contract_requests)
    op.execute(sa.text("DELETE FROM cm_purchase_orders"))

    # 3. Framework contracts (FK → third_parties, contract_companies, contracts, contract_requests)
    op.execute(sa.text("DELETE FROM cm_framework_contracts"))

    # 4. Contracts (FK → contract_requests, third_parties)
    op.execute(sa.text("DELETE FROM cm_contracts"))

    # 5. Magic links (FK → third_parties, contract_requests) — BEFORE contract_requests
    op.execute(sa.text("DELETE FROM tp_magic_links"))

    # 6. Webhook events (dedup tracking)
    op.execute(sa.text("DELETE FROM cm_webhook_events"))

    # 7. Contract requests (FK → third_parties, contract_companies)
    op.execute(sa.text("DELETE FROM cm_contract_requests"))

    # 8. Vigilance documents (FK → third_parties)
    op.execute(sa.text("DELETE FROM vig_documents"))

    # 9. Third parties (no more FKs pointing to them)
    op.execute(sa.text("DELETE FROM tp_third_parties"))

    # 10. Purge S3 contract files (best-effort, non-blocking)
    _purge_s3_contracts()

    # NOT deleted (configuration data):
    # - cm_contract_article_templates
    # - cm_contract_annex_templates
    # - cm_contract_companies


def downgrade() -> None:
    # Data migration — cannot be reversed automatically
    pass
