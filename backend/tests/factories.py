"""Test factories for creating test data."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.entities import (
    ApplicationStatus,
    Candidate,
    ContractType,
    Cooptation,
    Invitation,
    JobApplication,
    JobPosting,
    JobPostingStatus,
    Opportunity,
    PublishedOpportunity,
    User,
)
from app.domain.value_objects import (
    CooptationStatus,
    Email,
    OpportunityStatus,
    Phone,
    UserRole,
)
from app.infrastructure.security.password import hash_password


class UserFactory:
    """Factory for creating User entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        email: str | None = None,
        password: str = "TestPassword123!",
        first_name: str = "Test",
        last_name: str = "User",
        role: UserRole = UserRole.USER,
        is_verified: bool = True,
        is_active: bool = True,
        phone: str | None = None,
        boond_resource_id: str | None = None,
        manager_boond_id: str | None = None,
        **kwargs,
    ) -> User:
        """Create a User entity with sensible defaults."""
        cls._counter += 1

        if email is None:
            email = f"test-user-{cls._counter}-{uuid4().hex[:8]}@example.com"

        return User(
            id=kwargs.get("id", uuid4()),
            email=Email(email),
            first_name=first_name,
            last_name=last_name,
            password_hash=hash_password(password),
            role=role,
            is_verified=is_verified,
            is_active=is_active,
            phone=Phone(phone) if phone else None,
            boond_resource_id=boond_resource_id,
            manager_boond_id=manager_boond_id,
            verification_token=None if is_verified else "test-verification-token",
            reset_token=kwargs.get("reset_token"),
            reset_token_expires=kwargs.get("reset_token_expires"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
            updated_at=kwargs.get("updated_at", datetime.utcnow()),
        )

    @classmethod
    def create_admin(cls, **kwargs) -> User:
        """Create an admin user."""
        return cls.create(role=UserRole.ADMIN, **kwargs)

    @classmethod
    def create_commercial(cls, **kwargs) -> User:
        """Create a commercial user."""
        return cls.create(role=UserRole.COMMERCIAL, **kwargs)

    @classmethod
    def create_rh(cls, **kwargs) -> User:
        """Create an RH user."""
        return cls.create(role=UserRole.RH, **kwargs)

    @classmethod
    def create_unverified(cls, **kwargs) -> User:
        """Create an unverified user."""
        return cls.create(is_verified=False, **kwargs)

    @classmethod
    def create_inactive(cls, **kwargs) -> User:
        """Create an inactive user."""
        return cls.create(is_active=False, **kwargs)


class CandidateFactory:
    """Factory for creating Candidate entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        email: str | None = None,
        first_name: str = "Jean",
        last_name: str = "Dupont",
        civility: str = "M",
        phone: str | None = "+33612345678",
        daily_rate: float | None = 500.0,
        note: str | None = None,
        **kwargs,
    ) -> Candidate:
        """Create a Candidate entity."""
        cls._counter += 1

        if email is None:
            email = f"candidate-{cls._counter}-{uuid4().hex[:8]}@example.com"

        return Candidate(
            id=kwargs.get("id", uuid4()),
            email=Email(email),
            first_name=first_name,
            last_name=last_name,
            civility=civility,
            phone=Phone(phone) if phone else None,
            daily_rate=daily_rate,
            note=note,
            boond_candidate_id=kwargs.get("boond_candidate_id"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
        )


class OpportunityFactory:
    """Factory for creating Opportunity entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        title: str = "Développeur Python Senior",
        external_id: str | None = None,
        reference: str | None = None,
        budget: float | None = 600.0,
        manager_name: str | None = "Manager Test",
        manager_boond_id: str | None = None,
        client_name: str | None = "Client Test",
        description: str | None = "Description de l'opportunité",
        skills: list[str] | None = None,
        location: str | None = "Paris",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        is_active: bool = True,
        **kwargs,
    ) -> Opportunity:
        """Create an Opportunity entity."""
        cls._counter += 1

        if external_id is None:
            external_id = f"OPP-{cls._counter}-{uuid4().hex[:8]}"

        if reference is None:
            reference = f"REF-{cls._counter:04d}"

        return Opportunity(
            id=kwargs.get("id", uuid4()),
            external_id=external_id,
            title=title,
            reference=reference,
            budget=budget,
            manager_name=manager_name,
            manager_boond_id=manager_boond_id,
            client_name=client_name,
            description=description,
            skills=skills or ["Python", "FastAPI"],
            location=location,
            start_date=start_date,
            end_date=end_date,
            response_deadline=kwargs.get("response_deadline"),
            is_active=is_active,
            is_shared=kwargs.get("is_shared", True),
            owner_id=kwargs.get("owner_id"),
            synced_at=kwargs.get("synced_at", datetime.utcnow()),
            created_at=kwargs.get("created_at", datetime.utcnow()),
        )


class CooptationFactory:
    """Factory for creating Cooptation entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        candidate: Candidate | None = None,
        opportunity: Opportunity | None = None,
        submitter_id: str | None = None,
        status: CooptationStatus = CooptationStatus.PENDING,
        **kwargs,
    ) -> Cooptation:
        """Create a Cooptation entity."""
        cls._counter += 1

        if candidate is None:
            candidate = CandidateFactory.create()

        if opportunity is None:
            opportunity = OpportunityFactory.create()

        if submitter_id is None:
            submitter_id = str(uuid4())

        return Cooptation(
            id=kwargs.get("id", uuid4()),
            candidate_id=candidate.id,
            opportunity_id=opportunity.id,
            submitter_id=submitter_id,
            status=status,
            status_history=kwargs.get("status_history", []),
            external_positioning_id=kwargs.get("external_positioning_id"),
            rejection_reason=kwargs.get("rejection_reason"),
            submitted_at=kwargs.get("submitted_at", datetime.utcnow()),
            updated_at=kwargs.get("updated_at", datetime.utcnow()),
        )


class InvitationFactory:
    """Factory for creating Invitation entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        email: str | None = None,
        role: UserRole = UserRole.USER,
        invited_by: str | None = None,
        expires_at: datetime | None = None,
        **kwargs,
    ) -> Invitation:
        """Create an Invitation entity."""
        cls._counter += 1

        if email is None:
            email = f"invite-{cls._counter}-{uuid4().hex[:8]}@example.com"

        if invited_by is None:
            invited_by = str(uuid4())

        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=7)

        return Invitation(
            id=kwargs.get("id", uuid4()),
            email=email,
            role=role,
            token=kwargs.get("token", f"inv-token-{uuid4().hex}"),
            invited_by=invited_by,
            boond_resource_id=kwargs.get("boond_resource_id"),
            manager_boond_id=kwargs.get("manager_boond_id"),
            phone=kwargs.get("phone"),
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            expires_at=expires_at,
            accepted_at=kwargs.get("accepted_at"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
        )

    @classmethod
    def create_expired(cls, **kwargs) -> Invitation:
        """Create an expired invitation."""
        return cls.create(
            expires_at=datetime.utcnow() - timedelta(days=1),
            **kwargs,
        )


class JobPostingFactory:
    """Factory for creating JobPosting entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        title: str = "Développeur Python Senior",
        description: str | None = None,
        qualifications: str | None = None,
        opportunity_id: str | None = None,
        status: JobPostingStatus = JobPostingStatus.DRAFT,
        **kwargs,
    ) -> JobPosting:
        """Create a JobPosting entity."""
        cls._counter += 1

        if opportunity_id is None:
            opportunity_id = str(uuid4())

        # Minimum 500 chars for description
        if description is None:
            description = "D" * 500

        # Minimum 150 chars for qualifications
        if qualifications is None:
            qualifications = "Q" * 150

        return JobPosting(
            id=kwargs.get("id", uuid4()),
            opportunity_id=opportunity_id,
            title=title,
            description=description,
            qualifications=qualifications,
            location_country=kwargs.get("location_country", "France"),
            location_region=kwargs.get("location_region"),
            location_postal_code=kwargs.get("location_postal_code"),
            location_city=kwargs.get("location_city", "Paris"),
            contract_types=kwargs.get("contract_types", [ContractType.FREELANCE]),
            skills=kwargs.get("skills", ["Python", "FastAPI"]),
            salary_min_daily=kwargs.get("salary_min_daily"),
            salary_max_daily=kwargs.get("salary_max_daily"),
            salary_min_annual=kwargs.get("salary_min_annual"),
            salary_max_annual=kwargs.get("salary_max_annual"),
            remote=kwargs.get("remote"),
            experience_level=kwargs.get("experience_level"),
            start_date=kwargs.get("start_date"),
            duration_months=kwargs.get("duration_months"),
            status=status,
            turnoverit_reference=kwargs.get("turnoverit_reference"),
            created_by=kwargs.get("created_by"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
            updated_at=kwargs.get("updated_at", datetime.utcnow()),
            published_at=kwargs.get("published_at"),
            closed_at=kwargs.get("closed_at"),
        )


class JobApplicationFactory:
    """Factory for creating JobApplication entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        job_posting_id: str | None = None,
        email: str | None = None,
        first_name: str = "Jean",
        last_name: str = "Candidat",
        status: ApplicationStatus = ApplicationStatus.EN_COURS,
        **kwargs,
    ) -> JobApplication:
        """Create a JobApplication entity."""
        from datetime import date

        cls._counter += 1

        if job_posting_id is None:
            job_posting_id = str(uuid4())

        if email is None:
            email = f"applicant-{cls._counter}-{uuid4().hex[:8]}@example.com"

        return JobApplication(
            id=kwargs.get("id", uuid4()),
            job_posting_id=job_posting_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=kwargs.get("phone", "+33612345678"),
            job_title=kwargs.get("job_title", "Développeur Python"),
            tjm_min=kwargs.get("tjm_min", 450.0),
            tjm_max=kwargs.get("tjm_max", 550.0),
            availability_date=kwargs.get("availability_date", date.today() + timedelta(days=30)),
            cv_s3_key=kwargs.get("cv_s3_key", f"cvs/test/{uuid4()}.pdf"),
            cv_filename=kwargs.get("cv_filename", "CV_Test.pdf"),
            matching_score=kwargs.get("matching_score"),
            matching_details=kwargs.get("matching_details"),
            status=status,
            status_history=kwargs.get("status_history", []),
            notes=kwargs.get("notes"),
            boond_candidate_id=kwargs.get("boond_candidate_id"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
            updated_at=kwargs.get("updated_at", datetime.utcnow()),
        )


class PublishedOpportunityFactory:
    """Factory for creating PublishedOpportunity entities."""

    _counter = 0

    @classmethod
    def create(
        cls,
        title: str = "Mission Python Senior",
        description: str = "Description anonymisée de la mission",
        boond_opportunity_id: str | None = None,
        status: OpportunityStatus = OpportunityStatus.PUBLISHED,
        **kwargs,
    ) -> PublishedOpportunity:
        """Create a PublishedOpportunity entity."""
        cls._counter += 1

        if boond_opportunity_id is None:
            boond_opportunity_id = f"BOOND-{cls._counter}-{uuid4().hex[:8]}"

        return PublishedOpportunity(
            id=kwargs.get("id", uuid4()),
            boond_opportunity_id=boond_opportunity_id,
            title=title,
            description=description,
            skills=kwargs.get("skills", ["Python", "FastAPI", "PostgreSQL"]),
            original_title=kwargs.get("original_title", "Mission Client XYZ"),
            original_data=kwargs.get("original_data"),
            end_date=kwargs.get("end_date"),
            status=status,
            published_by=kwargs.get("published_by", str(uuid4())),
            created_at=kwargs.get("created_at", datetime.utcnow()),
            updated_at=kwargs.get("updated_at", datetime.utcnow()),
        )
