"""Compliance dashboard routes."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdvOrAdminUser
from app.infrastructure.database.connection import get_db
from app.third_party.infrastructure.adapters.postgres_third_party_repo import (
    ThirdPartyRepository,
)
from app.vigilance.api.schemas import ComplianceDashboardResponse
from app.vigilance.domain.value_objects.document_status import DocumentStatus
from app.vigilance.infrastructure.adapters.postgres_document_repo import DocumentRepository

logger = structlog.get_logger()

router = APIRouter(tags=["Compliance"])


@router.get(
    "/dashboard",
    response_model=ComplianceDashboardResponse,
    summary="Get compliance dashboard data",
)
async def get_compliance_dashboard(
    user_id: AdvOrAdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get compliance overview dashboard. ADV/admin only."""
    tp_repo = ThirdPartyRepository(db)
    doc_repo = DocumentRepository(db)

    # Third party counts by compliance status
    compliance_counts = await tp_repo.count_by_compliance()
    total = sum(compliance_counts.values())

    compliant = compliance_counts.get("compliant", 0)
    non_compliant = compliance_counts.get("non_compliant", 0)
    expiring_soon = compliance_counts.get("expiring_soon", 0)
    pending = compliance_counts.get("pending", 0)

    compliance_rate = (compliant / total * 100) if total > 0 else 0.0

    # Documents pending review (status = RECEIVED)
    # This requires listing all received docs across all third parties
    # Use a direct query for efficiency
    from sqlalchemy import func, select

    from app.vigilance.infrastructure.models import VigilanceDocumentModel

    received_count_result = await db.execute(
        select(func.count(VigilanceDocumentModel.id)).where(
            VigilanceDocumentModel.status == DocumentStatus.RECEIVED.value
        )
    )
    documents_pending_review = received_count_result.scalar_one()

    # Documents expiring soon
    expiring_docs = await doc_repo.list_expiring(days_ahead=30)
    documents_expiring_soon = len(expiring_docs)

    return ComplianceDashboardResponse(
        total_third_parties=total,
        compliant=compliant,
        non_compliant=non_compliant,
        expiring_soon=expiring_soon,
        pending=pending,
        compliance_rate=round(compliance_rate, 1),
        documents_pending_review=documents_pending_review,
        documents_expiring_soon=documents_expiring_soon,
    )
