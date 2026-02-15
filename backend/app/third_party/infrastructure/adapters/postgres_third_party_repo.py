"""PostgreSQL implementation of ThirdPartyRepository."""

from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.value_objects.compliance_status import ComplianceStatus
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType
from app.third_party.infrastructure.models import ThirdPartyModel

logger = structlog.get_logger()


class ThirdPartyRepository:
    """PostgreSQL-backed third party repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, third_party_id: UUID) -> ThirdParty | None:
        """Get third party by ID."""
        result = await self.session.execute(
            select(ThirdPartyModel).where(ThirdPartyModel.id == third_party_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_siren(self, siren: str) -> ThirdParty | None:
        """Get third party by SIREN number."""
        result = await self.session.execute(
            select(ThirdPartyModel).where(ThirdPartyModel.siren == siren)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, third_party: ThirdParty) -> ThirdParty:
        """Save third party (create or update)."""
        result = await self.session.execute(
            select(ThirdPartyModel).where(ThirdPartyModel.id == third_party.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.boond_provider_id = third_party.boond_provider_id
            model.type = third_party.type.value
            model.company_name = third_party.company_name
            model.legal_form = third_party.legal_form
            model.capital = third_party.capital
            model.siren = third_party.siren
            model.siret = third_party.siret
            model.rcs_city = third_party.rcs_city
            model.rcs_number = third_party.rcs_number
            model.head_office_address = third_party.head_office_address
            model.representative_name = third_party.representative_name
            model.representative_title = third_party.representative_title
            model.contact_email = third_party.contact_email
            model.compliance_status = third_party.compliance_status.value
        else:
            model = self._to_model(third_party)
            self.session.add(model)

        await self.session.flush()
        logger.info(
            "third_party_saved",
            third_party_id=str(third_party.id),
            siren=third_party.siren,
        )
        return self._to_entity(model)

    async def delete(self, third_party_id: UUID) -> bool:
        """Delete third party by ID."""
        result = await self.session.execute(
            select(ThirdPartyModel).where(ThirdPartyModel.id == third_party_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        compliance_status: ComplianceStatus | None = None,
        search: str | None = None,
        third_party_type: str | None = None,
    ) -> list[ThirdParty]:
        """List third parties with optional filters."""
        query = select(ThirdPartyModel)

        if compliance_status:
            query = query.where(ThirdPartyModel.compliance_status == compliance_status.value)
        if third_party_type:
            query = query.where(ThirdPartyModel.type == third_party_type)
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                ThirdPartyModel.company_name.ilike(search_filter)
                | ThirdPartyModel.siren.ilike(search_filter)
                | ThirdPartyModel.contact_email.ilike(search_filter)
            )

        query = query.order_by(ThirdPartyModel.company_name).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        compliance_status: ComplianceStatus | None = None,
        search: str | None = None,
        third_party_type: str | None = None,
    ) -> int:
        """Count third parties with optional filters."""
        query = select(func.count(ThirdPartyModel.id))

        if compliance_status:
            query = query.where(ThirdPartyModel.compliance_status == compliance_status.value)
        if third_party_type:
            query = query.where(ThirdPartyModel.type == third_party_type)
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                ThirdPartyModel.company_name.ilike(search_filter)
                | ThirdPartyModel.siren.ilike(search_filter)
            )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_by_compliance(self) -> dict[str, int]:
        """Count third parties grouped by compliance status."""
        query = select(
            ThirdPartyModel.compliance_status,
            func.count(ThirdPartyModel.id),
        ).group_by(ThirdPartyModel.compliance_status)

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    def _to_entity(self, model: ThirdPartyModel) -> ThirdParty:
        """Convert SQLAlchemy model to domain entity."""
        return ThirdParty(
            id=model.id,
            boond_provider_id=model.boond_provider_id,
            type=ThirdPartyType(model.type),
            company_name=model.company_name,
            legal_form=model.legal_form,
            capital=model.capital,
            siren=model.siren,
            siret=model.siret,
            rcs_city=model.rcs_city,
            rcs_number=model.rcs_number,
            head_office_address=model.head_office_address,
            representative_name=model.representative_name,
            representative_title=model.representative_title,
            contact_email=model.contact_email,
            compliance_status=ComplianceStatus(model.compliance_status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: ThirdParty) -> ThirdPartyModel:
        """Convert domain entity to SQLAlchemy model."""
        return ThirdPartyModel(
            id=entity.id,
            boond_provider_id=entity.boond_provider_id,
            type=entity.type.value,
            company_name=entity.company_name,
            legal_form=entity.legal_form,
            capital=entity.capital,
            siren=entity.siren,
            siret=entity.siret,
            rcs_city=entity.rcs_city,
            rcs_number=entity.rcs_number,
            head_office_address=entity.head_office_address,
            representative_name=entity.representative_name,
            representative_title=entity.representative_title,
            contact_email=entity.contact_email,
            compliance_status=entity.compliance_status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
