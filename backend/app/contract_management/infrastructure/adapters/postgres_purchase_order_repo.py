"""PostgreSQL implementation of the purchase order repository."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)
from app.contract_management.infrastructure.adapters.postgres_contract_repo import (
    _next_reference_number,
    _reference_lock_key,
)
from app.contract_management.infrastructure.models import (
    ContractCompanyModel,
    PurchaseOrderModel,
)

logger = structlog.get_logger()

# Un BDC annulé libère son positionnement : un nouveau peut être créé.
_LIVE_STATUSES = tuple(s.value for s in PurchaseOrderStatus if s != PurchaseOrderStatus.CANCELLED)


class PurchaseOrderRepository:
    """PostgreSQL-backed purchase order repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, purchase_order_id: UUID) -> PurchaseOrder | None:
        """Get a purchase order by ID."""
        result = await self.session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == purchase_order_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_positioning_id(self, positioning_id: int) -> PurchaseOrder | None:
        """Get the live purchase order created for a Boond positioning.

        Les BDC annulés sont exclus : le webhook peut alors en recréer un.
        Seul le **premier** BDC d'une mission porte cette contrainte — les
        reconductions, créées depuis Bobby, reprennent le même positionnement
        et sont distinguées par `parent_purchase_order_id`.
        """
        result = await self.session.execute(
            select(PurchaseOrderModel)
            .where(
                PurchaseOrderModel.boond_positioning_id == positioning_id,
                PurchaseOrderModel.parent_purchase_order_id.is_(None),
                PurchaseOrderModel.status.in_(_LIVE_STATUSES),
            )
            .order_by(PurchaseOrderModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_third_party(self, third_party_id: UUID) -> list[PurchaseOrder]:
        """List every purchase order of a supplier, most recent first."""
        result = await self.session.execute(
            select(PurchaseOrderModel)
            .where(PurchaseOrderModel.third_party_id == third_party_id)
            .order_by(PurchaseOrderModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_contract_request(self, contract_request_id: UUID) -> list[PurchaseOrder]:
        """List the purchase orders attached to a framework contract."""
        result = await self.session.execute(
            select(PurchaseOrderModel)
            .where(PurchaseOrderModel.contract_request_id == contract_request_id)
            .order_by(PurchaseOrderModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(  # noqa: PLR0913
        self,
        skip: int = 0,
        limit: int = 50,
        status: PurchaseOrderStatus | None = None,
        third_party_id: UUID | None = None,
        company_id: UUID | None = None,
        contract_request_id: UUID | None = None,
        search: str | None = None,
        exclude_cancelled: bool = False,
    ) -> list[PurchaseOrder]:
        """List purchase orders with optional filters."""
        query = self._filtered_query(
            select(PurchaseOrderModel),
            status,
            third_party_id,
            company_id,
            contract_request_id,
            search,
            exclude_cancelled,
        )
        query = query.order_by(PurchaseOrderModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(  # noqa: PLR0913
        self,
        status: PurchaseOrderStatus | None = None,
        third_party_id: UUID | None = None,
        company_id: UUID | None = None,
        contract_request_id: UUID | None = None,
        search: str | None = None,
        exclude_cancelled: bool = False,
    ) -> int:
        """Count purchase orders matching the same filters as `list_all`."""
        query = self._filtered_query(
            select(func.count(PurchaseOrderModel.id)),
            status,
            third_party_id,
            company_id,
            contract_request_id,
            search,
            exclude_cancelled,
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    def _filtered_query(  # noqa: PLR0913
        self,
        query,
        status: PurchaseOrderStatus | None,
        third_party_id: UUID | None,
        company_id: UUID | None,
        contract_request_id: UUID | None,
        search: str | None,
        exclude_cancelled: bool = False,
    ):
        """Apply the shared filters of `list_all` and `count`.

        `company_id` isole les missions d'une société émettrice : un fournisseur
        travaillant avec plusieurs sociétés du groupe a des missions distinctes
        pour chacune, qui ne doivent pas se mélanger.

        `exclude_cancelled` ne garde que les bons de commande vivants : un BDC
        annulé ne représente aucune mission et n'a rien à faire dans la liste.
        """
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        if exclude_cancelled:
            query = query.where(PurchaseOrderModel.status.in_(_LIVE_STATUSES))
        if third_party_id:
            query = query.where(PurchaseOrderModel.third_party_id == third_party_id)
        if company_id:
            query = query.where(PurchaseOrderModel.company_id == company_id)
        if contract_request_id:
            query = query.where(PurchaseOrderModel.contract_request_id == contract_request_id)
        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(PurchaseOrderModel.reference).like(pattern),
                    func.lower(PurchaseOrderModel.provisional_reference).like(pattern),
                    func.lower(PurchaseOrderModel.consultant_last_name).like(pattern),
                    func.lower(PurchaseOrderModel.consultant_first_name).like(pattern),
                    func.lower(PurchaseOrderModel.client_name).like(pattern),
                    func.lower(PurchaseOrderModel.mission_title).like(pattern),
                )
            )
        return query

    async def get_next_provisional_reference(self) -> str:
        """Generate the next provisional reference, format PROV-BDC-YYYY-NNN.

        Portée par le bon de commande tant qu'il n'est pas validé : un brouillon
        abandonné ne consomme ainsi aucun numéro de la séquence définitive, que
        le contrat cadre exige continue.
        """
        prefix = f"PROV-BDC-{datetime.utcnow().year}-"

        # Sérialise l'allocation pour cette famille de préfixe (anti-race
        # condition). Le verrou tient jusqu'au commit, couvrant l'insert.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"),
            {"k": _reference_lock_key(prefix)},
        )

        result = await self.session.execute(
            select(PurchaseOrderModel.provisional_reference).where(
                PurchaseOrderModel.provisional_reference.like(f"{prefix}%")
            )
        )
        return f"{prefix}{_next_reference_number(result.scalars().all()):03d}"

    async def get_next_reference(self, company_code: str | None = None) -> str:
        """Generate the next purchase order reference, format XXX-BDC-NNN.

        La séquence est propre à chaque société émettrice, comme celle des
        contrats cadres (XXX-CC-NNN). Sans code fourni, celui de la société par
        défaut est utilisé, avec repli sur "GEN".
        """
        if company_code is None:
            result = await self.session.execute(
                select(ContractCompanyModel.code)
                .where(
                    ContractCompanyModel.is_default.is_(True),
                    ContractCompanyModel.is_active.is_(True),
                )
                .limit(1)
            )
            code = result.scalar_one_or_none() or "GEN"
        else:
            code = company_code.upper()

        prefix = f"{code}-BDC-"

        # Sérialise l'allocation pour cette famille de préfixe (anti-race
        # condition). Le verrou tient jusqu'au commit, couvrant l'insert.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"),
            {"k": _reference_lock_key(prefix)},
        )

        # Tri numérique (et non lexicographique via MAX) : 1000 > 999.
        result = await self.session.execute(
            select(PurchaseOrderModel.reference).where(
                PurchaseOrderModel.reference.like(f"{prefix}%")
            )
        )
        next_num = _next_reference_number(result.scalars().all())

        return f"{prefix}{next_num:03d}"

    async def save(self, purchase_order: PurchaseOrder) -> PurchaseOrder:
        """Save a purchase order (create or update)."""
        result = await self.session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == purchase_order.id)
        )
        model = result.scalar_one_or_none()

        if model:
            for attr in (
                "provisional_reference",
                "reference",
                "company_id",
                "third_party_id",
                "contract_request_id",
                "parent_purchase_order_id",
                "boond_consultant_id",
                "boond_consultant_type",
                "consultant_civility",
                "consultant_first_name",
                "consultant_last_name",
                "consultant_email",
                "consultant_phone",
                "boond_positioning_id",
                "boond_need_id",
                "boond_delivery_id",
                "boond_project_id",
                "client_name",
                "mission_title",
                "mission_description",
                "mission_site_name",
                "mission_address",
                "mission_postal_code",
                "mission_city",
                "sale_daily_rate",
                "purchase_daily_rate",
                "days_sold",
                "free_days",
                "start_date",
                "end_date",
                "s3_key_draft",
                "s3_key_signed",
                "yousign_envelope_id",
                "sent_for_signature_at",
                "signed_at",
                "boond_contract_id",
                "boond_purchase_order_id",
                "boond_sync_error",
                "commercial_email",
                "created_by",
                "updated_at",
            ):
                setattr(model, attr, getattr(purchase_order, attr))
            model.status = purchase_order.status.value
            model.status_history = purchase_order.status_history
            flag_modified(model, "status_history")
        else:
            model = self._to_model(purchase_order)
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, purchase_order_id: UUID) -> bool:
        """Delete a purchase order permanently. Returns True if it existed."""
        result = await self.session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == purchase_order_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def list_expired_active(self, today: datetime) -> list[PurchaseOrder]:
        """List active purchase orders whose end date has passed."""
        result = await self.session.execute(
            select(PurchaseOrderModel).where(
                PurchaseOrderModel.status == PurchaseOrderStatus.ACTIVE.value,
                PurchaseOrderModel.end_date.is_not(None),
                PurchaseOrderModel.end_date < today.date(),
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: PurchaseOrderModel) -> PurchaseOrder:
        """Convert SQLAlchemy model to domain entity."""
        return PurchaseOrder(
            id=model.id,
            provisional_reference=model.provisional_reference,
            reference=model.reference,
            status=PurchaseOrderStatus(model.status),
            company_id=model.company_id,
            third_party_id=model.third_party_id,
            contract_request_id=model.contract_request_id,
            parent_purchase_order_id=model.parent_purchase_order_id,
            boond_consultant_id=model.boond_consultant_id,
            boond_consultant_type=model.boond_consultant_type,
            consultant_civility=model.consultant_civility,
            consultant_first_name=model.consultant_first_name,
            consultant_last_name=model.consultant_last_name,
            consultant_email=model.consultant_email,
            consultant_phone=model.consultant_phone,
            boond_positioning_id=model.boond_positioning_id,
            boond_need_id=model.boond_need_id,
            boond_delivery_id=model.boond_delivery_id,
            boond_project_id=model.boond_project_id,
            client_name=model.client_name,
            mission_title=model.mission_title,
            mission_description=model.mission_description,
            mission_site_name=model.mission_site_name,
            mission_address=model.mission_address,
            mission_postal_code=model.mission_postal_code,
            mission_city=model.mission_city,
            sale_daily_rate=model.sale_daily_rate,
            purchase_daily_rate=model.purchase_daily_rate,
            days_sold=model.days_sold,
            free_days=model.free_days,
            start_date=model.start_date,
            end_date=model.end_date,
            s3_key_draft=model.s3_key_draft,
            s3_key_signed=model.s3_key_signed,
            yousign_envelope_id=model.yousign_envelope_id,
            sent_for_signature_at=model.sent_for_signature_at,
            signed_at=model.signed_at,
            boond_contract_id=model.boond_contract_id,
            boond_purchase_order_id=model.boond_purchase_order_id,
            boond_sync_error=model.boond_sync_error,
            commercial_email=model.commercial_email,
            created_by=model.created_by,
            status_history=model.status_history or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: PurchaseOrder) -> PurchaseOrderModel:
        """Convert domain entity to SQLAlchemy model."""
        return PurchaseOrderModel(
            id=entity.id,
            provisional_reference=entity.provisional_reference,
            reference=entity.reference,
            status=entity.status.value,
            company_id=entity.company_id,
            third_party_id=entity.third_party_id,
            contract_request_id=entity.contract_request_id,
            parent_purchase_order_id=entity.parent_purchase_order_id,
            boond_consultant_id=entity.boond_consultant_id,
            boond_consultant_type=entity.boond_consultant_type,
            consultant_civility=entity.consultant_civility,
            consultant_first_name=entity.consultant_first_name,
            consultant_last_name=entity.consultant_last_name,
            consultant_email=entity.consultant_email,
            consultant_phone=entity.consultant_phone,
            boond_positioning_id=entity.boond_positioning_id,
            boond_need_id=entity.boond_need_id,
            boond_delivery_id=entity.boond_delivery_id,
            boond_project_id=entity.boond_project_id,
            client_name=entity.client_name,
            mission_title=entity.mission_title,
            mission_description=entity.mission_description,
            mission_site_name=entity.mission_site_name,
            mission_address=entity.mission_address,
            mission_postal_code=entity.mission_postal_code,
            mission_city=entity.mission_city,
            sale_daily_rate=entity.sale_daily_rate,
            purchase_daily_rate=entity.purchase_daily_rate,
            days_sold=entity.days_sold,
            free_days=entity.free_days,
            start_date=entity.start_date,
            end_date=entity.end_date,
            s3_key_draft=entity.s3_key_draft,
            s3_key_signed=entity.s3_key_signed,
            yousign_envelope_id=entity.yousign_envelope_id,
            sent_for_signature_at=entity.sent_for_signature_at,
            signed_at=entity.signed_at,
            boond_contract_id=entity.boond_contract_id,
            boond_purchase_order_id=entity.boond_purchase_order_id,
            boond_sync_error=entity.boond_sync_error,
            commercial_email=entity.commercial_email,
            created_by=entity.created_by,
            status_history=entity.status_history,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
