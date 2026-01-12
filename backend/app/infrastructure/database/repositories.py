"""SQLAlchemy repository implementations."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Candidate, Cooptation, Opportunity, User
from app.domain.value_objects import CooptationStatus, Email, Phone, UserRole
from app.infrastructure.database.models import (
    CandidateModel,
    CooptationModel,
    OpportunityModel,
    UserModel,
)


class UserRepository:
    """User repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by verification token."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.verification_token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by reset token."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.reset_token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        """Save user (create or update)."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        model = result.scalar_one_or_none()

        if model:
            # Update existing
            model.email = str(user.email).lower()
            model.password_hash = user.password_hash
            model.first_name = user.first_name
            model.last_name = user.last_name
            model.role = str(user.role)
            model.is_verified = user.is_verified
            model.is_active = user.is_active
            model.boond_resource_id = user.boond_resource_id
            model.verification_token = user.verification_token
            model.reset_token = user.reset_token
            model.reset_token_expires = user.reset_token_expires
            model.updated_at = datetime.utcnow()
        else:
            # Create new
            model = UserModel(
                id=user.id,
                email=str(user.email).lower(),
                password_hash=user.password_hash,
                first_name=user.first_name,
                last_name=user.last_name,
                role=str(user.role),
                is_verified=user.is_verified,
                is_active=user.is_active,
                boond_resource_id=user.boond_resource_id,
                verification_token=user.verification_token,
                reset_token=user.reset_token,
                reset_token_expires=user.reset_token_expires,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users with pagination."""
        result = await self.session.execute(
            select(UserModel).offset(skip).limit(limit).order_by(UserModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        """Count total users."""
        result = await self.session.execute(select(func.count(UserModel.id)))
        return result.scalar() or 0

    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity."""
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=model.password_hash,
            first_name=model.first_name,
            last_name=model.last_name,
            role=UserRole(model.role),
            is_verified=model.is_verified,
            is_active=model.is_active,
            boond_resource_id=model.boond_resource_id,
            verification_token=model.verification_token,
            reset_token=model.reset_token,
            reset_token_expires=model.reset_token_expires,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class CandidateRepository:
    """Candidate repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, candidate_id: UUID) -> Optional[Candidate]:
        """Get candidate by ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[Candidate]:
        """Get candidate by email."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_external_id(self, external_id: str) -> Optional[Candidate]:
        """Get candidate by external BoondManager ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.external_id == external_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, candidate: Candidate) -> Candidate:
        """Save candidate (create or update)."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.email = str(candidate.email).lower()
            model.first_name = candidate.first_name
            model.last_name = candidate.last_name
            model.civility = candidate.civility
            model.phone = str(candidate.phone) if candidate.phone else None
            model.cv_filename = candidate.cv_filename
            model.cv_path = candidate.cv_path
            model.daily_rate = candidate.daily_rate
            model.note = candidate.note
            model.external_id = candidate.external_id
            model.updated_at = datetime.utcnow()
        else:
            model = CandidateModel(
                id=candidate.id,
                email=str(candidate.email).lower(),
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                civility=candidate.civility,
                phone=str(candidate.phone) if candidate.phone else None,
                cv_filename=candidate.cv_filename,
                cv_path=candidate.cv_path,
                daily_rate=candidate.daily_rate,
                note=candidate.note,
                external_id=candidate.external_id,
                created_at=candidate.created_at,
                updated_at=candidate.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, candidate_id: UUID) -> bool:
        """Delete candidate by ID."""
        result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == candidate_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    def _to_entity(self, model: CandidateModel) -> Candidate:
        """Convert model to entity."""
        return Candidate(
            id=model.id,
            email=Email(model.email),
            first_name=model.first_name,
            last_name=model.last_name,
            civility=model.civility,
            phone=Phone(model.phone) if model.phone else None,
            cv_filename=model.cv_filename,
            cv_path=model.cv_path,
            daily_rate=model.daily_rate,
            note=model.note,
            external_id=model.external_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class OpportunityRepository:
    """Opportunity repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: UUID) -> Optional[Opportunity]:
        """Get opportunity by ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_external_id(self, external_id: str) -> Optional[Opportunity]:
        """Get opportunity by external BoondManager ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.external_id == external_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """Save opportunity (create or update)."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.external_id = opportunity.external_id
            model.title = opportunity.title
            model.reference = opportunity.reference
            model.start_date = opportunity.start_date
            model.end_date = opportunity.end_date
            model.response_deadline = opportunity.response_deadline
            model.budget = opportunity.budget
            model.manager_name = opportunity.manager_name
            model.manager_email = opportunity.manager_email
            model.client_name = opportunity.client_name
            model.description = opportunity.description
            model.skills = opportunity.skills
            model.location = opportunity.location
            model.is_active = opportunity.is_active
            model.synced_at = opportunity.synced_at
            model.updated_at = datetime.utcnow()
        else:
            model = OpportunityModel(
                id=opportunity.id,
                external_id=opportunity.external_id,
                title=opportunity.title,
                reference=opportunity.reference,
                start_date=opportunity.start_date,
                end_date=opportunity.end_date,
                response_deadline=opportunity.response_deadline,
                budget=opportunity.budget,
                manager_name=opportunity.manager_name,
                manager_email=opportunity.manager_email,
                client_name=opportunity.client_name,
                description=opportunity.description,
                skills=opportunity.skills,
                location=opportunity.location,
                is_active=opportunity.is_active,
                synced_at=opportunity.synced_at,
                created_at=opportunity.created_at,
                updated_at=opportunity.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def save_many(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Save multiple opportunities."""
        saved = []
        for opp in opportunities:
            saved.append(await self.save(opp))
        return saved

    async def delete(self, opportunity_id: UUID) -> bool:
        """Delete opportunity by ID."""
        result = await self.session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_active(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> list[Opportunity]:
        """List active opportunities with pagination and optional search."""
        query = select(OpportunityModel).where(OpportunityModel.is_active == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        query = query.offset(skip).limit(limit).order_by(OpportunityModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_active(self, search: Optional[str] = None) -> int:
        """Count active opportunities."""
        query = select(func.count(OpportunityModel.id)).where(
            OpportunityModel.is_active == True
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OpportunityModel.title.ilike(search_pattern),
                    OpportunityModel.reference.ilike(search_pattern),
                    OpportunityModel.client_name.ilike(search_pattern),
                )
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_last_sync_time(self) -> Optional[datetime]:
        """Get the most recent sync time."""
        result = await self.session.execute(
            select(func.max(OpportunityModel.synced_at))
        )
        return result.scalar()

    def _to_entity(self, model: OpportunityModel) -> Opportunity:
        """Convert model to entity."""
        return Opportunity(
            id=model.id,
            external_id=model.external_id,
            title=model.title,
            reference=model.reference,
            start_date=model.start_date,
            end_date=model.end_date,
            response_deadline=model.response_deadline,
            budget=model.budget,
            manager_name=model.manager_name,
            manager_email=model.manager_email,
            client_name=model.client_name,
            description=model.description,
            skills=model.skills or [],
            location=model.location,
            is_active=model.is_active,
            synced_at=model.synced_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class CooptationRepository:
    """Cooptation repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, cooptation_id: UUID) -> Optional[Cooptation]:
        """Get cooptation by ID with related entities."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.id == cooptation_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_candidate_email_and_opportunity(
        self,
        email: str,
        opportunity_id: UUID,
    ) -> Optional[Cooptation]:
        """Check if candidate already proposed for opportunity."""
        result = await self.session.execute(
            select(CooptationModel)
            .join(CandidateModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(
                CandidateModel.email == email.lower(),
                CooptationModel.opportunity_id == opportunity_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, cooptation: Cooptation) -> Cooptation:
        """Save cooptation (create or update)."""
        result = await self.session.execute(
            select(CooptationModel).where(CooptationModel.id == cooptation.id)
        )
        model = result.scalar_one_or_none()

        # Convert status history to JSON-serializable format
        status_history = [
            {
                "from_status": str(sh.from_status),
                "to_status": str(sh.to_status),
                "changed_at": sh.changed_at.isoformat(),
                "changed_by": str(sh.changed_by) if sh.changed_by else None,
                "comment": sh.comment,
            }
            for sh in cooptation.status_history
        ]

        if model:
            model.candidate_id = cooptation.candidate.id
            model.opportunity_id = cooptation.opportunity.id
            model.submitter_id = cooptation.submitter_id
            model.status = str(cooptation.status)
            model.external_positioning_id = cooptation.external_positioning_id
            model.status_history = status_history
            model.rejection_reason = cooptation.rejection_reason
            model.updated_at = datetime.utcnow()
        else:
            model = CooptationModel(
                id=cooptation.id,
                candidate_id=cooptation.candidate.id,
                opportunity_id=cooptation.opportunity.id,
                submitter_id=cooptation.submitter_id,
                status=str(cooptation.status),
                external_positioning_id=cooptation.external_positioning_id,
                status_history=status_history,
                rejection_reason=cooptation.rejection_reason,
                submitted_at=cooptation.submitted_at,
                updated_at=cooptation.updated_at,
            )
            self.session.add(model)

        await self.session.flush()

        # Reload with relationships
        return await self.get_by_id(cooptation.id)  # type: ignore

    async def delete(self, cooptation_id: UUID) -> bool:
        """Delete cooptation by ID."""
        result = await self.session.execute(
            select(CooptationModel).where(CooptationModel.id == cooptation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_by_submitter(
        self,
        submitter_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cooptation]:
        """List cooptations by submitter."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.submitter_id == submitter_id)
            .offset(skip)
            .limit(limit)
            .order_by(CooptationModel.submitted_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_status(
        self,
        status: CooptationStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Cooptation]:
        """List cooptations by status."""
        result = await self.session.execute(
            select(CooptationModel)
            .options(
                selectinload(CooptationModel.candidate),
                selectinload(CooptationModel.opportunity),
            )
            .where(CooptationModel.status == str(status))
            .offset(skip)
            .limit(limit)
            .order_by(CooptationModel.submitted_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CooptationStatus] = None,
    ) -> list[Cooptation]:
        """List all cooptations with optional status filter."""
        query = select(CooptationModel).options(
            selectinload(CooptationModel.candidate),
            selectinload(CooptationModel.opportunity),
        )

        if status:
            query = query.where(CooptationModel.status == str(status))

        query = query.offset(skip).limit(limit).order_by(CooptationModel.submitted_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count cooptations by submitter."""
        result = await self.session.execute(
            select(func.count(CooptationModel.id)).where(
                CooptationModel.submitter_id == submitter_id
            )
        )
        return result.scalar() or 0

    async def count_by_status(self, status: CooptationStatus) -> int:
        """Count cooptations by status."""
        result = await self.session.execute(
            select(func.count(CooptationModel.id)).where(
                CooptationModel.status == str(status)
            )
        )
        return result.scalar() or 0

    async def get_stats_by_submitter(self, submitter_id: UUID) -> dict[str, int]:
        """Get cooptation statistics for a submitter."""
        stats = {"total": 0, "pending": 0, "in_review": 0, "accepted": 0, "rejected": 0}

        for status in CooptationStatus:
            result = await self.session.execute(
                select(func.count(CooptationModel.id)).where(
                    CooptationModel.submitter_id == submitter_id,
                    CooptationModel.status == str(status),
                )
            )
            count = result.scalar() or 0
            stats[str(status)] = count
            stats["total"] += count

        return stats

    def _to_entity(self, model: CooptationModel) -> Cooptation:
        """Convert model to entity."""
        from app.domain.entities.cooptation import StatusChange

        # Convert candidate
        candidate = Candidate(
            id=model.candidate.id,
            email=Email(model.candidate.email),
            first_name=model.candidate.first_name,
            last_name=model.candidate.last_name,
            civility=model.candidate.civility,
            phone=Phone(model.candidate.phone) if model.candidate.phone else None,
            cv_filename=model.candidate.cv_filename,
            cv_path=model.candidate.cv_path,
            daily_rate=model.candidate.daily_rate,
            note=model.candidate.note,
            external_id=model.candidate.external_id,
            created_at=model.candidate.created_at,
            updated_at=model.candidate.updated_at,
        )

        # Convert opportunity
        opportunity = Opportunity(
            id=model.opportunity.id,
            external_id=model.opportunity.external_id,
            title=model.opportunity.title,
            reference=model.opportunity.reference,
            start_date=model.opportunity.start_date,
            end_date=model.opportunity.end_date,
            response_deadline=model.opportunity.response_deadline,
            budget=model.opportunity.budget,
            manager_name=model.opportunity.manager_name,
            manager_email=model.opportunity.manager_email,
            client_name=model.opportunity.client_name,
            description=model.opportunity.description,
            skills=model.opportunity.skills or [],
            location=model.opportunity.location,
            is_active=model.opportunity.is_active,
            synced_at=model.opportunity.synced_at,
            created_at=model.opportunity.created_at,
            updated_at=model.opportunity.updated_at,
        )

        # Convert status history
        status_history = []
        for sh in model.status_history or []:
            status_history.append(
                StatusChange(
                    from_status=CooptationStatus(sh["from_status"]),
                    to_status=CooptationStatus(sh["to_status"]),
                    changed_at=datetime.fromisoformat(sh["changed_at"]),
                    changed_by=UUID(sh["changed_by"]) if sh.get("changed_by") else None,
                    comment=sh.get("comment"),
                )
            )

        return Cooptation(
            id=model.id,
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=model.submitter_id,
            status=CooptationStatus(model.status),
            external_positioning_id=model.external_positioning_id,
            status_history=status_history,
            rejection_reason=model.rejection_reason,
            submitted_at=model.submitted_at,
            updated_at=model.updated_at,
        )
