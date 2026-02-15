"""PostgreSQL implementation of contract repositories."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.domain.entities.contract import Contract
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.infrastructure.models import (
    ContractModel,
    ContractRequestModel,
    WebhookEventModel,
)

logger = structlog.get_logger()


class ContractRequestRepository:
    """PostgreSQL-backed contract request repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, request_id: UUID) -> ContractRequest | None:
        """Get a contract request by ID."""
        result = await self.session.execute(
            select(ContractRequestModel).where(ContractRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_positioning_id(self, positioning_id: int) -> ContractRequest | None:
        """Get an active contract request by Boond positioning ID.

        Cancelled CRs are excluded so that a new one can be created
        for the same positioning after cancellation.
        """
        result = await self.session.execute(
            select(ContractRequestModel).where(
                ContractRequestModel.boond_positioning_id == positioning_id,
                ContractRequestModel.status != ContractRequestStatus.CANCELLED.value,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, request: ContractRequest) -> ContractRequest:
        """Save a contract request (create or update)."""
        result = await self.session.execute(
            select(ContractRequestModel).where(ContractRequestModel.id == request.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.status = request.status.value
            model.third_party_id = request.third_party_id
            model.third_party_type = request.third_party_type
            model.daily_rate = request.daily_rate
            model.start_date = request.start_date
            model.client_name = request.client_name
            model.mission_description = request.mission_description
            model.mission_location = request.mission_location
            model.contractualization_contact_email = request.contractualization_contact_email
            model.contract_config = request.contract_config
            model.commercial_validated_at = request.commercial_validated_at
            model.compliance_override = request.compliance_override
            model.compliance_override_reason = request.compliance_override_reason
            model.updated_at = request.updated_at
        else:
            model = self._to_model(request)
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        status: ContractRequestStatus | None = None,
    ) -> list[ContractRequest]:
        """List contract requests with optional status filter."""
        query = select(ContractRequestModel)
        if status:
            query = query.where(ContractRequestModel.status == status.value)
        query = query.order_by(ContractRequestModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self, status: ContractRequestStatus | None = None) -> int:
        """Count contract requests with optional status filter."""
        query = select(func.count(ContractRequestModel.id))
        if status:
            query = query.where(ContractRequestModel.status == status.value)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def list_by_commercial_email(
        self,
        email: str,
        skip: int = 0,
        limit: int = 50,
        status: ContractRequestStatus | None = None,
    ) -> list[ContractRequest]:
        """List contract requests for a specific commercial."""
        query = select(ContractRequestModel).where(
            func.lower(ContractRequestModel.commercial_email) == email.lower()
        )
        if status:
            query = query.where(ContractRequestModel.status == status.value)
        query = query.order_by(ContractRequestModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_commercial_email(
        self,
        email: str,
        status: ContractRequestStatus | None = None,
    ) -> int:
        """Count contract requests for a specific commercial."""
        query = select(func.count(ContractRequestModel.id)).where(
            func.lower(ContractRequestModel.commercial_email) == email.lower()
        )
        if status:
            query = query.where(ContractRequestModel.status == status.value)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_next_reference(self) -> str:
        """Generate the next contract request reference."""
        year = datetime.utcnow().year
        prefix = f"CR-{year}-"

        result = await self.session.execute(
            select(func.max(ContractRequestModel.reference)).where(
                ContractRequestModel.reference.like(f"{prefix}%")
            )
        )
        max_ref = result.scalar_one_or_none()

        if max_ref:
            try:
                last_num = int(max_ref.replace(prefix, ""))
                next_num = last_num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:04d}"

    def _to_entity(self, model: ContractRequestModel) -> ContractRequest:
        """Convert SQLAlchemy model to domain entity."""
        return ContractRequest(
            id=model.id,
            reference=model.reference,
            boond_positioning_id=model.boond_positioning_id,
            boond_candidate_id=model.boond_candidate_id,
            boond_need_id=model.boond_need_id,
            third_party_id=model.third_party_id,
            status=ContractRequestStatus(model.status),
            third_party_type=model.third_party_type,
            daily_rate=model.daily_rate,
            start_date=model.start_date,
            client_name=model.client_name,
            mission_description=model.mission_description,
            mission_location=model.mission_location,
            contractualization_contact_email=model.contractualization_contact_email,
            contract_config=model.contract_config,
            commercial_email=model.commercial_email,
            commercial_validated_at=model.commercial_validated_at,
            compliance_override=model.compliance_override,
            compliance_override_reason=model.compliance_override_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: ContractRequest) -> ContractRequestModel:
        """Convert domain entity to SQLAlchemy model."""
        return ContractRequestModel(
            id=entity.id,
            reference=entity.reference,
            boond_positioning_id=entity.boond_positioning_id,
            boond_candidate_id=entity.boond_candidate_id,
            boond_need_id=entity.boond_need_id,
            third_party_id=entity.third_party_id,
            status=entity.status.value,
            third_party_type=entity.third_party_type,
            daily_rate=entity.daily_rate,
            start_date=entity.start_date,
            client_name=entity.client_name,
            mission_description=entity.mission_description,
            mission_location=entity.mission_location,
            contractualization_contact_email=entity.contractualization_contact_email,
            contract_config=entity.contract_config,
            commercial_email=entity.commercial_email,
            commercial_validated_at=entity.commercial_validated_at,
            compliance_override=entity.compliance_override,
            compliance_override_reason=entity.compliance_override_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class ContractRepository:
    """PostgreSQL-backed contract repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, contract_id: UUID) -> Contract | None:
        """Get a contract by ID."""
        result = await self.session.execute(
            select(ContractModel).where(ContractModel.id == contract_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_request_id(self, request_id: UUID) -> Contract | None:
        """Get the latest contract for a request."""
        result = await self.session.execute(
            select(ContractModel)
            .where(ContractModel.contract_request_id == request_id)
            .order_by(ContractModel.version.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, contract: Contract) -> Contract:
        """Save a contract (create or update)."""
        result = await self.session.execute(
            select(ContractModel).where(ContractModel.id == contract.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.s3_key_draft = contract.s3_key_draft
            model.s3_key_signed = contract.s3_key_signed
            model.yousign_procedure_id = contract.yousign_procedure_id
            model.yousign_status = contract.yousign_status
            model.boond_purchase_order_id = contract.boond_purchase_order_id
            model.partner_comments = contract.partner_comments
            model.signed_at = contract.signed_at
        else:
            model = self._to_model(contract)
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    def _to_entity(self, model: ContractModel) -> Contract:
        """Convert SQLAlchemy model to domain entity."""
        return Contract(
            id=model.id,
            contract_request_id=model.contract_request_id,
            third_party_id=model.third_party_id,
            reference=model.reference,
            version=model.version,
            s3_key_draft=model.s3_key_draft,
            s3_key_signed=model.s3_key_signed,
            yousign_procedure_id=model.yousign_procedure_id,
            yousign_status=model.yousign_status,
            boond_purchase_order_id=model.boond_purchase_order_id,
            partner_comments=model.partner_comments,
            created_at=model.created_at,
            signed_at=model.signed_at,
        )

    def _to_model(self, entity: Contract) -> ContractModel:
        """Convert domain entity to SQLAlchemy model."""
        return ContractModel(
            id=entity.id,
            contract_request_id=entity.contract_request_id,
            third_party_id=entity.third_party_id,
            reference=entity.reference,
            version=entity.version,
            s3_key_draft=entity.s3_key_draft,
            s3_key_signed=entity.s3_key_signed,
            yousign_procedure_id=entity.yousign_procedure_id,
            yousign_status=entity.yousign_status,
            boond_purchase_order_id=entity.boond_purchase_order_id,
            partner_comments=entity.partner_comments,
            created_at=entity.created_at,
            signed_at=entity.signed_at,
        )


class WebhookEventRepository:
    """PostgreSQL-backed webhook event repository for deduplication."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, event_id: str) -> bool:
        """Check if an event has been processed."""
        result = await self.session.execute(
            select(WebhookEventModel).where(WebhookEventModel.event_id == event_id)
        )
        return result.scalar_one_or_none() is not None

    async def save(self, event_id: str, event_type: str, payload: dict) -> None:
        """Save an event for deduplication."""
        model = WebhookEventModel(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(model)
        await self.session.flush()

    async def delete_by_prefix(self, prefix: str) -> int:
        """Delete webhook events matching a prefix.

        Returns:
            Number of deleted rows.
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(WebhookEventModel).where(
                WebhookEventModel.event_id.like(f"{prefix}%")
            )
        )
        await self.session.flush()
        return result.rowcount
