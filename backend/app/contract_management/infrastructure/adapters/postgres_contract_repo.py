"""PostgreSQL implementation of contract repositories."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract_management.domain.entities.contract import Contract
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.infrastructure.models import (
    ContractCompanyModel,
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
            model.reference = request.reference
            model.third_party_id = request.third_party_id
            model.third_party_type = request.third_party_type
            model.daily_rate = request.daily_rate
            model.quantity_sold = request.quantity_sold
            model.start_date = request.start_date
            model.end_date = request.end_date
            model.client_name = request.client_name
            model.mission_title = request.mission_title
            model.mission_description = request.mission_description
            model.consultant_civility = request.consultant_civility
            model.consultant_first_name = request.consultant_first_name
            model.consultant_last_name = request.consultant_last_name
            model.consultant_email = request.consultant_email
            model.consultant_phone = request.consultant_phone
            model.mission_site_name = request.mission_site_name
            model.mission_address = request.mission_address
            model.mission_postal_code = request.mission_postal_code
            model.mission_city = request.mission_city
            model.contractualization_contact_email = request.contractualization_contact_email
            model.contract_config = request.contract_config
            flag_modified(model, "contract_config")
            model.company_id = request.company_id
            model.commercial_validated_at = request.commercial_validated_at
            model.compliance_override = request.compliance_override
            model.compliance_override_reason = request.compliance_override_reason
            model.status_history = request.status_history
            flag_modified(model, "status_history")
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
            func.lower(ContractRequestModel.commercial_email) == str(email).lower()
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
            func.lower(ContractRequestModel.commercial_email) == str(email).lower()
        )
        if status:
            query = query.where(ContractRequestModel.status == status.value)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_next_provisional_reference(self) -> str:
        """Generate the next provisional reference in format PROV-YYYY-NNNN."""
        year = datetime.utcnow().year
        prefix = f"PROV-{year}-"

        result = await self.session.execute(
            select(func.max(ContractRequestModel.provisional_reference)).where(
                ContractRequestModel.provisional_reference.like(f"{prefix}%")
            )
        )
        max_ref = result.scalar_one_or_none()

        if max_ref:
            try:
                last_num = int(max_ref.rsplit("-", 1)[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:04d}"

    async def get_company_by_boond_agency_id(self, agency_id: int) -> UUID | None:
        """Return the company_id matching a Boond agency ID, or None."""
        result = await self.session.execute(
            select(ContractCompanyModel.id).where(
                ContractCompanyModel.boond_agency_id == agency_id,
                ContractCompanyModel.is_active.is_(True),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_reference(self, company_code: str | None = None) -> str:
        """Generate the next final contract reference in format XXX-YYYY-NNNN.

        The sequence counter is independent per company code.
        If company_code is not provided, the default company's code is used.
        Falls back to "GEN" if no default company exists.
        """
        if company_code is None:
            # Fetch the default company's code
            result = await self.session.execute(
                select(ContractCompanyModel.code).where(
                    ContractCompanyModel.is_default.is_(True),
                    ContractCompanyModel.is_active.is_(True),
                ).limit(1)
            )
            code = result.scalar_one_or_none() or "GEN"
        else:
            code = company_code.upper()

        year = datetime.utcnow().year
        prefix = f"{code}-{year}-"

        result = await self.session.execute(
            select(func.max(ContractRequestModel.reference)).where(
                ContractRequestModel.reference.like(f"{prefix}%")
            )
        )
        max_ref = result.scalar_one_or_none()

        if max_ref:
            try:
                last_num = int(max_ref.rsplit("-", 1)[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:04d}"

    def _to_entity(self, model: ContractRequestModel) -> ContractRequest:
        """Convert SQLAlchemy model to domain entity."""
        return ContractRequest(
            id=model.id,
            provisional_reference=model.provisional_reference,
            reference=model.reference,
            boond_positioning_id=model.boond_positioning_id,
            boond_candidate_id=model.boond_candidate_id,
            boond_consultant_type=model.boond_consultant_type,
            boond_need_id=model.boond_need_id,
            third_party_id=model.third_party_id,
            status=ContractRequestStatus(model.status),
            third_party_type=model.third_party_type,
            daily_rate=model.daily_rate,
            quantity_sold=model.quantity_sold,
            start_date=model.start_date,
            end_date=model.end_date,
            client_name=model.client_name,
            mission_title=model.mission_title,
            mission_description=model.mission_description,
            consultant_civility=model.consultant_civility,
            consultant_first_name=model.consultant_first_name,
            consultant_last_name=model.consultant_last_name,
            consultant_email=model.consultant_email,
            consultant_phone=model.consultant_phone,
            mission_site_name=model.mission_site_name,
            mission_address=model.mission_address,
            mission_postal_code=model.mission_postal_code,
            mission_city=model.mission_city,
            contractualization_contact_email=model.contractualization_contact_email,
            contract_config=model.contract_config,
            company_id=model.company_id,
            commercial_email=model.commercial_email,
            commercial_validated_at=model.commercial_validated_at,
            compliance_override=model.compliance_override,
            compliance_override_reason=model.compliance_override_reason,
            status_history=model.status_history or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: ContractRequest) -> ContractRequestModel:
        """Convert domain entity to SQLAlchemy model."""
        return ContractRequestModel(
            id=entity.id,
            provisional_reference=entity.provisional_reference,
            reference=entity.reference,
            boond_positioning_id=entity.boond_positioning_id,
            boond_candidate_id=entity.boond_candidate_id,
            boond_consultant_type=entity.boond_consultant_type,
            boond_need_id=entity.boond_need_id,
            third_party_id=entity.third_party_id,
            status=entity.status.value,
            third_party_type=entity.third_party_type,
            daily_rate=entity.daily_rate,
            quantity_sold=entity.quantity_sold,
            start_date=entity.start_date,
            end_date=entity.end_date,
            client_name=entity.client_name,
            mission_title=entity.mission_title,
            mission_description=entity.mission_description,
            consultant_civility=entity.consultant_civility,
            consultant_first_name=entity.consultant_first_name,
            consultant_last_name=entity.consultant_last_name,
            consultant_email=entity.consultant_email,
            consultant_phone=entity.consultant_phone,
            mission_site_name=entity.mission_site_name,
            mission_address=entity.mission_address,
            mission_postal_code=entity.mission_postal_code,
            mission_city=entity.mission_city,
            contractualization_contact_email=entity.contractualization_contact_email,
            contract_config=entity.contract_config,
            company_id=entity.company_id,
            commercial_email=entity.commercial_email,
            commercial_validated_at=entity.commercial_validated_at,
            compliance_override=entity.compliance_override,
            compliance_override_reason=entity.compliance_override_reason,
            status_history=entity.status_history,
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

    async def list_by_contract_request(self, request_id: UUID) -> list[Contract]:
        """List all contracts for a contract request, ordered by version."""
        result = await self.session.execute(
            select(ContractModel)
            .where(ContractModel.contract_request_id == request_id)
            .order_by(ContractModel.version.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

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
            delete(WebhookEventModel).where(WebhookEventModel.event_id.like(f"{prefix}%"))
        )
        await self.session.flush()
        return result.rowcount
