"""Cooptation use cases."""

from dataclasses import dataclass
from uuid import UUID

from app.application.read_models.cooptation import (
    CooptationListReadModel,
    CooptationReadModel,
    CooptationStatsReadModel,
    StatusChangeReadModel,
)
from app.domain.entities import Candidate, Cooptation, Opportunity
from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    CooptationNotFoundError,
    OpportunityNotFoundError,
)
from app.domain.value_objects import CooptationStatus, Email, Phone
from app.infrastructure.boond.client import BoondClient
from app.infrastructure.database.repositories import (
    CandidateRepository,
    CooptationRepository,
    OpportunityRepository,
    PublishedOpportunityRepository,
    UserRepository,
)
from app.infrastructure.email.sender import EmailService


@dataclass
class CreateCooptationCommand:
    """Command for creating a cooptation."""

    opportunity_id: UUID
    submitter_id: UUID
    candidate_first_name: str
    candidate_last_name: str
    candidate_email: str
    candidate_civility: str = "M"
    candidate_phone: str | None = None
    candidate_daily_rate: float | None = None
    candidate_note: str | None = None


class CreateCooptationUseCase:
    """Use case for creating a cooptation."""

    def __init__(
        self,
        cooptation_repository: CooptationRepository,
        candidate_repository: CandidateRepository,
        opportunity_repository: OpportunityRepository,
        published_opportunity_repository: PublishedOpportunityRepository,
        user_repository: UserRepository,
        boond_client: BoondClient,
        email_service: EmailService,
    ) -> None:
        self.cooptation_repository = cooptation_repository
        self.candidate_repository = candidate_repository
        self.opportunity_repository = opportunity_repository
        self.published_opportunity_repository = published_opportunity_repository
        self.user_repository = user_repository
        self.boond_client = boond_client
        self.email_service = email_service

    async def execute(self, command: CreateCooptationCommand) -> CooptationReadModel:
        """Create a new cooptation."""
        # Check if opportunity exists in regular opportunities
        opportunity = await self.opportunity_repository.get_by_id(command.opportunity_id)

        # If not found, check in published opportunities
        if not opportunity:
            published = await self.published_opportunity_repository.get_by_id(
                command.opportunity_id
            )
            if published:
                # Convert PublishedOpportunity to Opportunity for the cooptation
                opportunity = Opportunity(
                    id=published.id,
                    title=published.title,
                    reference=f"PUB-{published.boond_opportunity_id}",
                    external_id=published.boond_opportunity_id,
                    description=published.description,
                    skills=published.skills,
                    end_date=published.end_date,
                    is_active=published.status.is_visible_to_consultants,
                    is_shared=True,
                    owner_id=published.published_by,
                    created_at=published.created_at,
                    updated_at=published.updated_at,
                )
                # Save to opportunities table for foreign key constraint
                opportunity = await self.opportunity_repository.save(opportunity)

        if not opportunity:
            raise OpportunityNotFoundError(str(command.opportunity_id))

        # Check for duplicate cooptation
        existing = await self.cooptation_repository.get_by_candidate_email_and_opportunity(
            email=command.candidate_email,
            opportunity_id=command.opportunity_id,
        )
        if existing:
            raise CandidateAlreadyExistsError(command.candidate_email)

        # Create or get candidate
        candidate = await self.candidate_repository.get_by_email(command.candidate_email)
        if not candidate:
            candidate = Candidate(
                email=Email(command.candidate_email),
                first_name=command.candidate_first_name,
                last_name=command.candidate_last_name,
                civility=command.candidate_civility,
                phone=Phone(command.candidate_phone) if command.candidate_phone else None,
                daily_rate=command.candidate_daily_rate,
                note=command.candidate_note,
            )
            candidate = await self.candidate_repository.save(candidate)

        # Create candidate in Boond if not exists
        if not candidate.external_id:
            try:
                external_id = await self.boond_client.create_candidate(candidate)
                candidate.update_external_id(external_id)
                await self.candidate_repository.save(candidate)
            except Exception:
                # Continue without Boond integration
                pass

        # Create cooptation
        cooptation = Cooptation(
            candidate=candidate,
            opportunity=opportunity,
            submitter_id=command.submitter_id,
            status=CooptationStatus.PENDING,
        )

        # Create positioning in Boond if possible
        if candidate.external_id and opportunity.external_id:
            try:
                positioning_id = await self.boond_client.create_positioning(
                    candidate_external_id=candidate.external_id,
                    opportunity_external_id=opportunity.external_id,
                )
                cooptation.update_external_positioning_id(positioning_id)
            except Exception:
                # Continue without Boond positioning
                pass

        saved = await self.cooptation_repository.save(cooptation)

        # Get submitter for email
        submitter = await self.user_repository.get_by_id(command.submitter_id)
        if submitter:
            await self.email_service.send_cooptation_confirmation(
                to=str(submitter.email),
                name=submitter.first_name,
                candidate_name=candidate.full_name,
                opportunity_title=opportunity.title,
            )

        return self._to_read_model(saved)

    def _to_read_model(self, cooptation: Cooptation) -> CooptationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in cooptation.status_history
        ]

        return CooptationReadModel(
            id=str(cooptation.id),
            candidate_id=str(cooptation.candidate.id),
            candidate_name=cooptation.candidate.full_name,
            candidate_email=str(cooptation.candidate.email),
            candidate_phone=(
                str(cooptation.candidate.phone) if cooptation.candidate.phone else None
            ),
            candidate_daily_rate=cooptation.candidate.daily_rate,
            opportunity_id=str(cooptation.opportunity.id),
            opportunity_title=cooptation.opportunity.title,
            opportunity_reference=cooptation.opportunity.reference,
            status=str(cooptation.status),
            status_display=cooptation.status.display_name,
            submitter_id=str(cooptation.submitter_id),
            external_positioning_id=cooptation.external_positioning_id,
            rejection_reason=cooptation.rejection_reason,
            status_history=status_history,
            submitted_at=cooptation.submitted_at,
            updated_at=cooptation.updated_at,
        )


class ListCooptationsUseCase:
    """Use case for listing cooptations."""

    def __init__(
        self,
        cooptation_repository: CooptationRepository,
        user_repository: UserRepository,
    ) -> None:
        self.cooptation_repository = cooptation_repository
        self.user_repository = user_repository

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        submitter_id: UUID | None = None,
        status: CooptationStatus | None = None,
    ) -> CooptationListReadModel:
        """List cooptations with pagination and filters."""
        skip = (page - 1) * page_size

        if submitter_id:
            cooptations = await self.cooptation_repository.list_by_submitter(
                submitter_id=submitter_id,
                skip=skip,
                limit=page_size,
            )
            total = await self.cooptation_repository.count_by_submitter(submitter_id)
        else:
            cooptations = await self.cooptation_repository.list_all(
                skip=skip,
                limit=page_size,
                status=status,
            )
            if status:
                total = await self.cooptation_repository.count_by_status(status)
            else:
                # Count all - sum of all statuses
                stats = await self.cooptation_repository.get_stats_by_submitter(
                    submitter_id or UUID(int=0)
                )
                total = stats.get("total", 0)

        # Get submitter names
        items = []
        for cooptation in cooptations:
            item = self._to_read_model(cooptation)
            submitter = await self.user_repository.get_by_id(cooptation.submitter_id)
            if submitter:
                item = CooptationReadModel(
                    **{**item.model_dump(), "submitter_name": submitter.full_name}
                )
            items.append(item)

        return CooptationListReadModel(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _to_read_model(self, cooptation: Cooptation) -> CooptationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in cooptation.status_history
        ]

        return CooptationReadModel(
            id=str(cooptation.id),
            candidate_id=str(cooptation.candidate.id),
            candidate_name=cooptation.candidate.full_name,
            candidate_email=str(cooptation.candidate.email),
            candidate_phone=(
                str(cooptation.candidate.phone) if cooptation.candidate.phone else None
            ),
            candidate_daily_rate=cooptation.candidate.daily_rate,
            opportunity_id=str(cooptation.opportunity.id),
            opportunity_title=cooptation.opportunity.title,
            opportunity_reference=cooptation.opportunity.reference,
            status=str(cooptation.status),
            status_display=cooptation.status.display_name,
            submitter_id=str(cooptation.submitter_id),
            external_positioning_id=cooptation.external_positioning_id,
            rejection_reason=cooptation.rejection_reason,
            status_history=status_history,
            submitted_at=cooptation.submitted_at,
            updated_at=cooptation.updated_at,
        )


class GetCooptationUseCase:
    """Use case for getting a single cooptation."""

    def __init__(self, cooptation_repository: CooptationRepository) -> None:
        self.cooptation_repository = cooptation_repository

    async def execute(self, cooptation_id: UUID) -> CooptationReadModel:
        """Get cooptation by ID."""
        cooptation = await self.cooptation_repository.get_by_id(cooptation_id)
        if not cooptation:
            raise CooptationNotFoundError(str(cooptation_id))

        return self._to_read_model(cooptation)

    def _to_read_model(self, cooptation: Cooptation) -> CooptationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in cooptation.status_history
        ]

        return CooptationReadModel(
            id=str(cooptation.id),
            candidate_id=str(cooptation.candidate.id),
            candidate_name=cooptation.candidate.full_name,
            candidate_email=str(cooptation.candidate.email),
            candidate_phone=(
                str(cooptation.candidate.phone) if cooptation.candidate.phone else None
            ),
            candidate_daily_rate=cooptation.candidate.daily_rate,
            opportunity_id=str(cooptation.opportunity.id),
            opportunity_title=cooptation.opportunity.title,
            opportunity_reference=cooptation.opportunity.reference,
            status=str(cooptation.status),
            status_display=cooptation.status.display_name,
            submitter_id=str(cooptation.submitter_id),
            external_positioning_id=cooptation.external_positioning_id,
            rejection_reason=cooptation.rejection_reason,
            status_history=status_history,
            submitted_at=cooptation.submitted_at,
            updated_at=cooptation.updated_at,
        )


class UpdateCooptationStatusUseCase:
    """Use case for updating cooptation status."""

    def __init__(
        self,
        cooptation_repository: CooptationRepository,
        user_repository: UserRepository,
        email_service: EmailService,
    ) -> None:
        self.cooptation_repository = cooptation_repository
        self.user_repository = user_repository
        self.email_service = email_service

    async def execute(
        self,
        cooptation_id: UUID,
        new_status: CooptationStatus,
        changed_by: UUID,
        comment: str | None = None,
    ) -> CooptationReadModel:
        """Update cooptation status."""
        cooptation = await self.cooptation_repository.get_by_id(cooptation_id)
        if not cooptation:
            raise CooptationNotFoundError(str(cooptation_id))

        success = cooptation.change_status(
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )

        if not success:
            raise ValueError(f"Invalid status transition from {cooptation.status} to {new_status}")

        saved = await self.cooptation_repository.save(cooptation)

        # Send notification to submitter
        submitter = await self.user_repository.get_by_id(cooptation.submitter_id)
        if submitter:
            await self.email_service.send_cooptation_status_update(
                to=str(submitter.email),
                name=submitter.first_name,
                candidate_name=cooptation.candidate.full_name,
                opportunity_title=cooptation.opportunity.title,
                new_status=str(new_status),
            )

        return self._to_read_model(saved)

    def _to_read_model(self, cooptation: Cooptation) -> CooptationReadModel:
        status_history = [
            StatusChangeReadModel(
                from_status=str(sh.from_status),
                to_status=str(sh.to_status),
                changed_at=sh.changed_at,
                changed_by=str(sh.changed_by) if sh.changed_by else None,
                comment=sh.comment,
            )
            for sh in cooptation.status_history
        ]

        return CooptationReadModel(
            id=str(cooptation.id),
            candidate_id=str(cooptation.candidate.id),
            candidate_name=cooptation.candidate.full_name,
            candidate_email=str(cooptation.candidate.email),
            candidate_phone=(
                str(cooptation.candidate.phone) if cooptation.candidate.phone else None
            ),
            candidate_daily_rate=cooptation.candidate.daily_rate,
            opportunity_id=str(cooptation.opportunity.id),
            opportunity_title=cooptation.opportunity.title,
            opportunity_reference=cooptation.opportunity.reference,
            status=str(cooptation.status),
            status_display=cooptation.status.display_name,
            submitter_id=str(cooptation.submitter_id),
            external_positioning_id=cooptation.external_positioning_id,
            rejection_reason=cooptation.rejection_reason,
            status_history=status_history,
            submitted_at=cooptation.submitted_at,
            updated_at=cooptation.updated_at,
        )


class GetCooptationStatsUseCase:
    """Use case for getting cooptation statistics."""

    def __init__(self, cooptation_repository: CooptationRepository) -> None:
        self.cooptation_repository = cooptation_repository

    async def execute(self, submitter_id: UUID | None = None) -> CooptationStatsReadModel:
        """Get cooptation statistics."""
        if submitter_id:
            stats = await self.cooptation_repository.get_stats_by_submitter(submitter_id)
        else:
            # Get overall stats
            stats = {
                "total": 0,
                "pending": await self.cooptation_repository.count_by_status(
                    CooptationStatus.PENDING
                ),
                "in_review": await self.cooptation_repository.count_by_status(
                    CooptationStatus.IN_REVIEW
                ),
                "interview": await self.cooptation_repository.count_by_status(
                    CooptationStatus.INTERVIEW
                ),
                "accepted": await self.cooptation_repository.count_by_status(
                    CooptationStatus.ACCEPTED
                ),
                "rejected": await self.cooptation_repository.count_by_status(
                    CooptationStatus.REJECTED
                ),
            }
            stats["total"] = sum(
                stats[k] for k in ["pending", "in_review", "interview", "accepted", "rejected"]
            )

        total = stats.get("total", 0)
        accepted = stats.get("accepted", 0)
        conversion_rate = (accepted / total * 100) if total > 0 else 0.0

        return CooptationStatsReadModel(
            total=total,
            pending=stats.get("pending", 0),
            in_review=stats.get("in_review", 0),
            interview=stats.get("interview", 0),
            accepted=accepted,
            rejected=stats.get("rejected", 0),
            conversion_rate=round(conversion_rate, 2),
        )
