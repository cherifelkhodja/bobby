"""SQLAlchemy repository implementations."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import (
    ApplicationStatus,
    BusinessLead,
    Candidate,
    Cooptation,
    CvTemplate,
    CvTransformationLog,
    Invitation,
    JobApplication,
    JobPosting,
    JobPostingStatus,
    Opportunity,
    User,
)
from app.domain.entities.business_lead import BusinessLeadStatus
from app.domain.value_objects import CooptationStatus, Email, Phone, UserRole
from app.infrastructure.database.models import (
    BusinessLeadModel,
    CandidateModel,
    CooptationModel,
    CvTemplateModel,
    CvTransformationLogModel,
    InvitationModel,
    JobApplicationModel,
    JobPostingModel,
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
            model.manager_boond_id = user.manager_boond_id
            model.phone = user.phone
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
                manager_boond_id=user.manager_boond_id,
                phone=user.phone,
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
            manager_boond_id=model.manager_boond_id,
            phone=model.phone,
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
            model.manager_boond_id = opportunity.manager_boond_id
            model.client_name = opportunity.client_name
            model.description = opportunity.description
            model.skills = opportunity.skills
            model.location = opportunity.location
            model.is_active = opportunity.is_active
            model.is_shared = opportunity.is_shared
            model.owner_id = opportunity.owner_id
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
                manager_boond_id=opportunity.manager_boond_id,
                client_name=opportunity.client_name,
                description=opportunity.description,
                skills=opportunity.skills,
                location=opportunity.location,
                is_active=opportunity.is_active,
                is_shared=opportunity.is_shared,
                owner_id=opportunity.owner_id,
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

    async def list_shared(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> list[Opportunity]:
        """List shared opportunities available for cooptation."""
        query = select(OpportunityModel).where(
            OpportunityModel.is_active == True,
            OpportunityModel.is_shared == True,
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

        query = query.offset(skip).limit(limit).order_by(OpportunityModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_shared(self, search: Optional[str] = None) -> int:
        """Count shared opportunities."""
        query = select(func.count(OpportunityModel.id)).where(
            OpportunityModel.is_active == True,
            OpportunityModel.is_shared == True,
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

    async def list_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """List opportunities owned by a specific user (commercial)."""
        query = (
            select(OpportunityModel)
            .where(OpportunityModel.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(OpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_manager_boond_id(
        self,
        manager_boond_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """List opportunities managed by a specific manager (via BoondManager ID)."""
        query = (
            select(OpportunityModel)
            .where(OpportunityModel.manager_boond_id == manager_boond_id)
            .offset(skip)
            .limit(limit)
            .order_by(OpportunityModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

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
            manager_boond_id=model.manager_boond_id,
            client_name=model.client_name,
            description=model.description,
            skills=model.skills or [],
            location=model.location,
            is_active=model.is_active,
            is_shared=model.is_shared,
            owner_id=model.owner_id,
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
            manager_boond_id=model.opportunity.manager_boond_id,
            client_name=model.opportunity.client_name,
            description=model.opportunity.description,
            skills=model.opportunity.skills or [],
            location=model.opportunity.location,
            is_active=model.opportunity.is_active,
            is_shared=model.opportunity.is_shared,
            owner_id=model.opportunity.owner_id,
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


class InvitationRepository:
    """Invitation repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invitation_id: UUID) -> Optional[Invitation]:
        """Get invitation by ID."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[Invitation]:
        """Get pending invitation by email."""
        result = await self.session.execute(
            select(InvitationModel).where(
                InvitationModel.email == email.lower(),
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, invitation: Invitation) -> Invitation:
        """Save invitation (create or update)."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.email = str(invitation.email).lower()
            model.role = str(invitation.role)
            model.token = invitation.token
            model.invited_by = invitation.invited_by
            model.expires_at = invitation.expires_at
            model.accepted_at = invitation.accepted_at
            model.boond_resource_id = invitation.boond_resource_id
            model.manager_boond_id = invitation.manager_boond_id
            model.phone = invitation.phone
            model.first_name = invitation.first_name
            model.last_name = invitation.last_name
        else:
            model = InvitationModel(
                id=invitation.id,
                email=str(invitation.email).lower(),
                role=str(invitation.role),
                token=invitation.token,
                invited_by=invitation.invited_by,
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                boond_resource_id=invitation.boond_resource_id,
                manager_boond_id=invitation.manager_boond_id,
                phone=invitation.phone,
                first_name=invitation.first_name,
                last_name=invitation.last_name,
                created_at=invitation.created_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, invitation_id: UUID) -> bool:
        """Delete invitation by ID."""
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_pending(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invitation]:
        """List pending (not accepted, not expired) invitations."""
        result = await self.session.execute(
            select(InvitationModel)
            .where(
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
            .offset(skip)
            .limit(limit)
            .order_by(InvitationModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invitation]:
        """List all invitations."""
        result = await self.session.execute(
            select(InvitationModel)
            .offset(skip)
            .limit(limit)
            .order_by(InvitationModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_pending(self) -> int:
        """Count pending invitations."""
        result = await self.session.execute(
            select(func.count(InvitationModel.id)).where(
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar() or 0

    def _to_entity(self, model: InvitationModel) -> Invitation:
        """Convert model to entity."""
        return Invitation(
            id=model.id,
            email=Email(model.email),
            role=UserRole(model.role),
            token=model.token,
            invited_by=model.invited_by,
            expires_at=model.expires_at,
            accepted_at=model.accepted_at,
            boond_resource_id=model.boond_resource_id,
            manager_boond_id=model.manager_boond_id,
            phone=model.phone,
            first_name=model.first_name,
            last_name=model.last_name,
            created_at=model.created_at,
        )


class BusinessLeadRepository:
    """Business Lead repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, lead_id: UUID) -> Optional[BusinessLead]:
        """Get business lead by ID."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, lead: BusinessLead) -> BusinessLead:
        """Save business lead (create or update)."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.title = lead.title
            model.description = lead.description
            model.submitter_id = lead.submitter_id
            model.client_name = lead.client_name
            model.contact_name = lead.contact_name
            model.contact_email = lead.contact_email
            model.contact_phone = lead.contact_phone
            model.estimated_budget = lead.estimated_budget
            model.expected_start_date = lead.expected_start_date
            model.skills_needed = lead.skills_needed
            model.location = lead.location
            model.status = str(lead.status)
            model.rejection_reason = lead.rejection_reason
            model.notes = lead.notes
            model.updated_at = datetime.utcnow()
        else:
            model = BusinessLeadModel(
                id=lead.id,
                title=lead.title,
                description=lead.description,
                submitter_id=lead.submitter_id,
                client_name=lead.client_name,
                contact_name=lead.contact_name,
                contact_email=lead.contact_email,
                contact_phone=lead.contact_phone,
                estimated_budget=lead.estimated_budget,
                expected_start_date=lead.expected_start_date,
                skills_needed=lead.skills_needed,
                location=lead.location,
                status=str(lead.status),
                rejection_reason=lead.rejection_reason,
                notes=lead.notes,
                created_at=lead.created_at,
                updated_at=lead.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, lead_id: UUID) -> bool:
        """Delete business lead by ID."""
        result = await self.session.execute(
            select(BusinessLeadModel).where(BusinessLeadModel.id == lead_id)
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
    ) -> list[BusinessLead]:
        """List business leads by submitter."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .where(BusinessLeadModel.submitter_id == submitter_id)
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_manager(
        self,
        manager_boond_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads visible to a manager (via submitter's manager_boond_id)."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .join(UserModel, BusinessLeadModel.submitter_id == UserModel.id)
            .where(UserModel.manager_boond_id == manager_boond_id)
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_status(
        self,
        status: BusinessLeadStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BusinessLead]:
        """List business leads by status."""
        result = await self.session.execute(
            select(BusinessLeadModel)
            .where(BusinessLeadModel.status == str(status))
            .offset(skip)
            .limit(limit)
            .order_by(BusinessLeadModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BusinessLeadStatus] = None,
    ) -> list[BusinessLead]:
        """List all business leads with optional status filter."""
        query = select(BusinessLeadModel)

        if status:
            query = query.where(BusinessLeadModel.status == str(status))

        query = query.offset(skip).limit(limit).order_by(BusinessLeadModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_submitter(self, submitter_id: UUID) -> int:
        """Count business leads by submitter."""
        result = await self.session.execute(
            select(func.count(BusinessLeadModel.id)).where(
                BusinessLeadModel.submitter_id == submitter_id
            )
        )
        return result.scalar() or 0

    async def count_by_status(self, status: BusinessLeadStatus) -> int:
        """Count business leads by status."""
        result = await self.session.execute(
            select(func.count(BusinessLeadModel.id)).where(
                BusinessLeadModel.status == str(status)
            )
        )
        return result.scalar() or 0

    def _to_entity(self, model: BusinessLeadModel) -> BusinessLead:
        """Convert model to entity."""
        return BusinessLead(
            id=model.id,
            title=model.title,
            description=model.description,
            submitter_id=model.submitter_id,
            client_name=model.client_name,
            contact_name=model.contact_name,
            contact_email=model.contact_email,
            contact_phone=model.contact_phone,
            estimated_budget=model.estimated_budget,
            expected_start_date=model.expected_start_date,
            skills_needed=model.skills_needed or [],
            location=model.location,
            status=BusinessLeadStatus(model.status),
            rejection_reason=model.rejection_reason,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class CvTemplateRepository:
    """CV Template repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, template_id: UUID) -> Optional[CvTemplate]:
        """Get template by ID."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Optional[CvTemplate]:
        """Get template by unique name."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, template: CvTemplate) -> CvTemplate:
        """Save template (create or update)."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.name = template.name
            model.display_name = template.display_name
            model.description = template.description
            model.file_content = template.file_content
            model.file_name = template.file_name
            model.is_active = template.is_active
            model.updated_at = datetime.utcnow()
        else:
            model = CvTemplateModel(
                id=template.id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                file_content=template.file_content,
                file_name=template.file_name,
                is_active=template.is_active,
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, template_id: UUID) -> bool:
        """Delete template by ID."""
        result = await self.session.execute(
            select(CvTemplateModel).where(CvTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_active(self) -> list[CvTemplate]:
        """List all active templates."""
        result = await self.session.execute(
            select(CvTemplateModel)
            .where(CvTemplateModel.is_active == True)
            .order_by(CvTemplateModel.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(self) -> list[CvTemplate]:
        """List all templates (including inactive)."""
        result = await self.session.execute(
            select(CvTemplateModel).order_by(CvTemplateModel.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: CvTemplateModel) -> CvTemplate:
        """Convert model to entity."""
        return CvTemplate(
            id=model.id,
            name=model.name,
            display_name=model.display_name,
            description=model.description,
            file_content=model.file_content,
            file_name=model.file_name,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class CvTransformationLogRepository:
    """CV Transformation Log repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, log: CvTransformationLog) -> CvTransformationLog:
        """Save transformation log."""
        model = CvTransformationLogModel(
            id=log.id,
            user_id=log.user_id,
            template_id=log.template_id,
            template_name=log.template_name,
            original_filename=log.original_filename,
            success=log.success,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def count_by_user(self, user_id: UUID, success_only: bool = True) -> int:
        """Count transformations by user."""
        query = select(func.count(CvTransformationLogModel.id)).where(
            CvTransformationLogModel.user_id == user_id
        )
        if success_only:
            query = query.where(CvTransformationLogModel.success == True)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_stats_by_user(self) -> list[dict]:
        """Get transformation stats grouped by user.

        Returns a list of dicts with user_id, user_email, user_name, and count.
        """
        result = await self.session.execute(
            select(
                CvTransformationLogModel.user_id,
                UserModel.email,
                UserModel.first_name,
                UserModel.last_name,
                func.count(CvTransformationLogModel.id).label("count"),
            )
            .join(UserModel, CvTransformationLogModel.user_id == UserModel.id)
            .where(CvTransformationLogModel.success == True)
            .group_by(
                CvTransformationLogModel.user_id,
                UserModel.email,
                UserModel.first_name,
                UserModel.last_name,
            )
            .order_by(func.count(CvTransformationLogModel.id).desc())
        )

        return [
            {
                "user_id": str(row.user_id),
                "user_email": row.email,
                "user_name": f"{row.first_name} {row.last_name}",
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_total_count(self, success_only: bool = True) -> int:
        """Get total transformation count."""
        query = select(func.count(CvTransformationLogModel.id))
        if success_only:
            query = query.where(CvTransformationLogModel.success == True)
        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_entity(self, model: CvTransformationLogModel) -> CvTransformationLog:
        """Convert model to entity."""
        return CvTransformationLog(
            id=model.id,
            user_id=model.user_id,
            template_id=model.template_id,
            template_name=model.template_name,
            original_filename=model.original_filename,
            success=model.success,
            error_message=model.error_message,
            created_at=model.created_at,
        )


class JobPostingRepository:
    """Job posting repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, posting_id: UUID) -> Optional[JobPosting]:
        """Get job posting by ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> Optional[JobPosting]:
        """Get job posting by application token (for public form)."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.application_token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_opportunity_id(self, opportunity_id: UUID) -> Optional[JobPosting]:
        """Get job posting by opportunity ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.opportunity_id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_turnoverit_reference(self, reference: str) -> Optional[JobPosting]:
        """Get job posting by Turnover-IT reference."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.turnoverit_reference == reference)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, posting: JobPosting) -> JobPosting:
        """Save job posting (create or update)."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting.id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.opportunity_id = posting.opportunity_id
            model.title = posting.title
            model.description = posting.description
            model.qualifications = posting.qualifications
            model.location_country = posting.location_country
            model.location_region = posting.location_region
            model.location_postal_code = posting.location_postal_code
            model.location_city = posting.location_city
            model.contract_types = [str(ct) for ct in posting.contract_types]
            model.skills = posting.skills
            model.experience_level = str(posting.experience_level) if posting.experience_level else None
            model.remote = str(posting.remote) if posting.remote else None
            model.start_date = posting.start_date
            model.duration_months = posting.duration_months
            model.salary_min_annual = posting.salary_min_annual
            model.salary_max_annual = posting.salary_max_annual
            model.salary_min_daily = posting.salary_min_daily
            model.salary_max_daily = posting.salary_max_daily
            model.employer_overview = posting.employer_overview
            model.status = str(posting.status)
            model.turnoverit_reference = posting.turnoverit_reference
            model.turnoverit_public_url = posting.turnoverit_public_url
            model.application_token = posting.application_token
            model.created_by = posting.created_by
            model.published_at = posting.published_at
            model.closed_at = posting.closed_at
            model.updated_at = datetime.utcnow()
        else:
            model = JobPostingModel(
                id=posting.id,
                opportunity_id=posting.opportunity_id,
                title=posting.title,
                description=posting.description,
                qualifications=posting.qualifications,
                location_country=posting.location_country,
                location_region=posting.location_region,
                location_postal_code=posting.location_postal_code,
                location_city=posting.location_city,
                contract_types=[str(ct) for ct in posting.contract_types],
                skills=posting.skills,
                experience_level=str(posting.experience_level) if posting.experience_level else None,
                remote=str(posting.remote) if posting.remote else None,
                start_date=posting.start_date,
                duration_months=posting.duration_months,
                salary_min_annual=posting.salary_min_annual,
                salary_max_annual=posting.salary_max_annual,
                salary_min_daily=posting.salary_min_daily,
                salary_max_daily=posting.salary_max_daily,
                employer_overview=posting.employer_overview,
                status=str(posting.status),
                turnoverit_reference=posting.turnoverit_reference,
                turnoverit_public_url=posting.turnoverit_public_url,
                application_token=posting.application_token,
                created_by=posting.created_by,
                published_at=posting.published_at,
                closed_at=posting.closed_at,
                created_at=posting.created_at,
                updated_at=posting.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, posting_id: UUID) -> bool:
        """Delete job posting by ID."""
        result = await self.session.execute(
            select(JobPostingModel).where(JobPostingModel.id == posting_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[JobPostingStatus] = None,
    ) -> list[JobPosting]:
        """List all job postings with optional status filter."""
        query = select(JobPostingModel)

        if status:
            query = query.where(JobPostingModel.status == str(status))

        query = query.offset(skip).limit(limit).order_by(JobPostingModel.created_at.desc())
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_created_by(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        """List job postings created by a specific user."""
        query = (
            select(JobPostingModel)
            .where(JobPostingModel.created_by == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(JobPostingModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_all(self, status: Optional[JobPostingStatus] = None) -> int:
        """Count all job postings with optional status filter."""
        query = select(func.count(JobPostingModel.id))

        if status:
            query = query.where(JobPostingModel.status == str(status))

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_entity(self, model: JobPostingModel) -> JobPosting:
        """Convert model to entity."""
        from app.domain.entities.job_posting import (
            ContractType,
            ExperienceLevel,
            RemotePolicy,
        )

        return JobPosting(
            id=model.id,
            opportunity_id=model.opportunity_id,
            title=model.title,
            description=model.description,
            qualifications=model.qualifications,
            location_country=model.location_country,
            location_region=model.location_region,
            location_postal_code=model.location_postal_code,
            location_city=model.location_city,
            contract_types=[ContractType(ct) for ct in (model.contract_types or [])],
            skills=model.skills or [],
            experience_level=ExperienceLevel(model.experience_level) if model.experience_level else None,
            remote=RemotePolicy(model.remote) if model.remote else None,
            start_date=model.start_date,
            duration_months=model.duration_months,
            salary_min_annual=model.salary_min_annual,
            salary_max_annual=model.salary_max_annual,
            salary_min_daily=model.salary_min_daily,
            salary_max_daily=model.salary_max_daily,
            employer_overview=model.employer_overview,
            status=JobPostingStatus(model.status),
            turnoverit_reference=model.turnoverit_reference,
            turnoverit_public_url=model.turnoverit_public_url,
            application_token=model.application_token,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            published_at=model.published_at,
            closed_at=model.closed_at,
        )


class JobApplicationRepository:
    """Job application repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, application_id: UUID) -> Optional[JobApplication]:
        """Get job application by ID."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, application: JobApplication) -> JobApplication:
        """Save job application (create or update)."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application.id)
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
            for sh in application.status_history
        ]

        # Convert matching details to JSON-serializable format
        matching_details = None
        if application.matching_details:
            matching_details = {
                "score": application.matching_details.score,
                "strengths": application.matching_details.strengths,
                "gaps": application.matching_details.gaps,
                "summary": application.matching_details.summary,
            }

        if model:
            model.job_posting_id = application.job_posting_id
            model.first_name = application.first_name
            model.last_name = application.last_name
            model.email = application.email
            model.phone = application.phone
            model.job_title = application.job_title
            model.tjm_min = application.tjm_min
            model.tjm_max = application.tjm_max
            model.availability_date = application.availability_date
            model.cv_s3_key = application.cv_s3_key
            model.cv_filename = application.cv_filename
            model.cv_text = application.cv_text
            model.matching_score = application.matching_score
            model.matching_details = matching_details
            model.status = str(application.status)
            model.status_history = status_history
            model.notes = application.notes
            model.boond_candidate_id = application.boond_candidate_id
            model.updated_at = datetime.utcnow()
        else:
            model = JobApplicationModel(
                id=application.id,
                job_posting_id=application.job_posting_id,
                first_name=application.first_name,
                last_name=application.last_name,
                email=application.email,
                phone=application.phone,
                job_title=application.job_title,
                tjm_min=application.tjm_min,
                tjm_max=application.tjm_max,
                availability_date=application.availability_date,
                cv_s3_key=application.cv_s3_key,
                cv_filename=application.cv_filename,
                cv_text=application.cv_text,
                matching_score=application.matching_score,
                matching_details=matching_details,
                status=str(application.status),
                status_history=status_history,
                notes=application.notes,
                boond_candidate_id=application.boond_candidate_id,
                created_at=application.created_at,
                updated_at=application.updated_at,
            )
            self.session.add(model)

        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, application_id: UUID) -> bool:
        """Delete job application by ID."""
        result = await self.session.execute(
            select(JobApplicationModel).where(JobApplicationModel.id == application_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False

    async def list_by_posting(
        self,
        posting_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
        sort_by_score: bool = True,
    ) -> list[JobApplication]:
        """List applications for a specific job posting."""
        query = select(JobApplicationModel).where(
            JobApplicationModel.job_posting_id == posting_id
        )

        if status:
            query = query.where(JobApplicationModel.status == str(status))

        if sort_by_score:
            # Sort by matching score descending, nulls last
            query = query.order_by(
                JobApplicationModel.matching_score.desc().nulls_last(),
                JobApplicationModel.created_at.desc(),
            )
        else:
            query = query.order_by(JobApplicationModel.created_at.desc())

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_posting(
        self,
        posting_id: UUID,
        status: Optional[ApplicationStatus] = None,
    ) -> int:
        """Count applications for a specific job posting."""
        query = select(func.count(JobApplicationModel.id)).where(
            JobApplicationModel.job_posting_id == posting_id
        )

        if status:
            query = query.where(JobApplicationModel.status == str(status))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_new_by_posting(self, posting_id: UUID) -> int:
        """Count new (unread) applications for a job posting."""
        return await self.count_by_posting(posting_id, ApplicationStatus.NOUVEAU)

    async def get_stats_by_posting(self, posting_id: UUID) -> dict[str, int]:
        """Get application statistics for a job posting."""
        stats = {"total": 0}

        for status in ApplicationStatus:
            count = await self.count_by_posting(posting_id, status)
            stats[str(status)] = count
            stats["total"] += count

        return stats

    async def exists_by_email_and_posting(
        self,
        email: str,
        posting_id: UUID,
    ) -> bool:
        """Check if an application already exists for this email and posting."""
        result = await self.session.execute(
            select(func.count(JobApplicationModel.id)).where(
                JobApplicationModel.email == email.lower(),
                JobApplicationModel.job_posting_id == posting_id,
            )
        )
        return (result.scalar() or 0) > 0

    def _to_entity(self, model: JobApplicationModel) -> JobApplication:
        """Convert model to entity."""
        from app.domain.entities.job_application import MatchingResult, StatusChange

        # Convert status history
        status_history = []
        for sh in model.status_history or []:
            status_history.append(
                StatusChange(
                    from_status=ApplicationStatus(sh["from_status"]),
                    to_status=ApplicationStatus(sh["to_status"]),
                    changed_at=datetime.fromisoformat(sh["changed_at"]),
                    changed_by=UUID(sh["changed_by"]) if sh.get("changed_by") else None,
                    comment=sh.get("comment"),
                )
            )

        # Convert matching details
        matching_details = None
        if model.matching_details:
            matching_details = MatchingResult(
                score=model.matching_details.get("score", 0),
                strengths=model.matching_details.get("strengths", []),
                gaps=model.matching_details.get("gaps", []),
                summary=model.matching_details.get("summary", ""),
            )

        return JobApplication(
            id=model.id,
            job_posting_id=model.job_posting_id,
            first_name=model.first_name,
            last_name=model.last_name,
            email=model.email,
            phone=model.phone,
            job_title=model.job_title,
            tjm_min=model.tjm_min,
            tjm_max=model.tjm_max,
            availability_date=model.availability_date,
            cv_s3_key=model.cv_s3_key,
            cv_filename=model.cv_filename,
            cv_text=model.cv_text,
            matching_score=model.matching_score,
            matching_details=matching_details,
            status=ApplicationStatus(model.status),
            status_history=status_history,
            notes=model.notes,
            boond_candidate_id=model.boond_candidate_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
