"""Job posting domain entity for Turnover-IT integration."""

import secrets
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4


class JobPostingStatus(str, Enum):
    """Job posting lifecycle status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable status name in French."""
        names = {
            JobPostingStatus.DRAFT: "Brouillon",
            JobPostingStatus.PUBLISHED: "Publiée",
            JobPostingStatus.CLOSED: "Fermée",
        }
        return names[self]

    @property
    def is_active(self) -> bool:
        """Check if posting is active (accepting applications)."""
        return self == JobPostingStatus.PUBLISHED


class ContractType(str, Enum):
    """Contract types for Turnover-IT.

    Valid values as per Turnover-IT API (JobConnect v2):
    - PERMANENT: CDI
    - TEMPORARY: CDD
    - FREELANCE: Freelance
    """

    PERMANENT = "PERMANENT"  # CDI
    TEMPORARY = "TEMPORARY"  # CDD
    FREELANCE = "FREELANCE"

    @property
    def display_name(self) -> str:
        """Human-readable contract type in French."""
        names = {
            ContractType.PERMANENT: "CDI",
            ContractType.TEMPORARY: "CDD",
            ContractType.FREELANCE: "Freelance",
        }
        return names[self]


class RemotePolicy(str, Enum):
    """Remote work policy for Turnover-IT."""

    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"

    @property
    def display_name(self) -> str:
        """Human-readable remote policy in French."""
        names = {
            RemotePolicy.NONE: "Présentiel",
            RemotePolicy.PARTIAL: "Hybride",
            RemotePolicy.FULL: "Full remote",
        }
        return names[self]


class ExperienceLevel(str, Enum):
    """Experience level for Turnover-IT."""

    JUNIOR = "JUNIOR"  # 0-2 years
    INTERMEDIATE = "INTERMEDIATE"  # 3-5 years
    SENIOR = "SENIOR"  # 6-10 years
    EXPERT = "EXPERT"  # > 10 years

    @property
    def display_name(self) -> str:
        """Human-readable experience level in French."""
        names = {
            ExperienceLevel.JUNIOR: "Junior (0-2 ans)",
            ExperienceLevel.INTERMEDIATE: "Intermédiaire (3-5 ans)",
            ExperienceLevel.SENIOR: "Senior (6-10 ans)",
            ExperienceLevel.EXPERT: "Expert (10+ ans)",
        }
        return names[self]


@dataclass
class JobPosting:
    """Job posting entity for publishing opportunities to Turnover-IT.

    This entity manages the lifecycle of a job posting from draft creation
    through publication on Turnover-IT and eventual closing.
    """

    # Required fields
    opportunity_id: UUID
    title: str  # 5-100 characters (Turnover-IT requirement)
    description: str  # 500-3000 characters (Turnover-IT requirement)
    qualifications: str  # 150-3000 characters (Turnover-IT requirement)
    location_country: str  # ISO country code (e.g., "France")

    # Location details (optional)
    location_region: str | None = None
    location_postal_code: str | None = None
    location_city: str | None = None
    location_key: str | None = None  # Turnover-IT location key for normalization

    # Job details
    contract_types: list[str] = field(default_factory=lambda: ["PERMANENT"])
    skills: list[str] = field(default_factory=list)
    experience_level: str | None = None
    remote: str | None = None
    start_date: date | None = None
    duration_months: int | None = None

    # Salary information
    salary_min_annual: float | None = None
    salary_max_annual: float | None = None
    salary_min_daily: float | None = None  # TJM min
    salary_max_daily: float | None = None  # TJM max

    # Company description (optional)
    employer_overview: str | None = None

    # Status and tracking
    status: JobPostingStatus = JobPostingStatus.DRAFT

    # Turnover-IT integration
    turnoverit_reference: str | None = None  # Our reference sent to Turnover-IT
    turnoverit_public_url: str | None = None  # URL on Turnover-IT/Free-Work

    # Public application form
    application_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))

    # Audit fields
    created_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Generate turnoverit_reference if not set."""
        if not self.turnoverit_reference:
            self.turnoverit_reference = f"ESN-{self.id.hex[:12].upper()}"

    @property
    def is_published(self) -> bool:
        """Check if job posting is currently published."""
        return self.status == JobPostingStatus.PUBLISHED

    @property
    def is_draft(self) -> bool:
        """Check if job posting is still a draft."""
        return self.status == JobPostingStatus.DRAFT

    @property
    def is_closed(self) -> bool:
        """Check if job posting is closed."""
        return self.status == JobPostingStatus.CLOSED

    @property
    def application_url_path(self) -> str:
        """Get the public application URL path."""
        return f"/postuler/{self.application_token}"

    def validate_for_publication(self) -> list[str]:
        """Validate job posting before publication.

        Returns:
            List of validation errors. Empty if valid.
        """
        errors: list[str] = []

        # Title validation (5-100 chars)
        if len(self.title) < 5:
            errors.append("Le titre doit contenir au moins 5 caractères")
        if len(self.title) > 100:
            errors.append("Le titre ne doit pas dépasser 100 caractères")

        # Description validation (500-3000 chars)
        if len(self.description) < 500:
            errors.append("La description doit contenir au moins 500 caractères")
        if len(self.description) > 3000:
            errors.append("La description ne doit pas dépasser 3000 caractères")

        # Qualifications validation (150-3000 chars)
        if len(self.qualifications) < 150:
            errors.append("Les qualifications doivent contenir au moins 150 caractères")
        if len(self.qualifications) > 3000:
            errors.append("Les qualifications ne doivent pas dépasser 3000 caractères")

        # Location validation
        if not self.location_country:
            errors.append("Le pays est obligatoire")

        # Contract types validation
        if not self.contract_types:
            errors.append("Au moins un type de contrat est requis")

        return errors

    def publish(self, turnoverit_public_url: str | None = None) -> None:
        """Mark job posting as published.

        Args:
            turnoverit_public_url: URL on Turnover-IT/Free-Work if available.

        Raises:
            ValueError: If posting has validation errors.
        """
        errors = self.validate_for_publication()
        if errors:
            raise ValueError(f"Cannot publish: {'; '.join(errors)}")

        if self.status == JobPostingStatus.CLOSED:
            raise ValueError("Cannot publish a closed job posting")

        self.status = JobPostingStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if turnoverit_public_url:
            self.turnoverit_public_url = turnoverit_public_url

    def close(self) -> None:
        """Close job posting (stop accepting applications)."""
        self.status = JobPostingStatus.CLOSED
        self.closed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def reopen(self) -> None:
        """Reopen a closed job posting as draft."""
        if not self.is_closed:
            raise ValueError("Can only reopen a closed job posting")

        self.status = JobPostingStatus.DRAFT
        self.closed_at = None
        self.updated_at = datetime.utcnow()

    def update_details(
        self,
        title: str | None = None,
        description: str | None = None,
        qualifications: str | None = None,
        skills: list[str] | None = None,
        experience_level: str | None = None,
        remote: str | None = None,
        salary_min_daily: float | None = None,
        salary_max_daily: float | None = None,
    ) -> None:
        """Update job posting details (only allowed in draft status)."""
        if not self.is_draft:
            raise ValueError("Can only update details of a draft job posting")

        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if qualifications is not None:
            self.qualifications = qualifications
        if skills is not None:
            self.skills = skills
        if experience_level is not None:
            self.experience_level = experience_level
        if remote is not None:
            self.remote = remote
        if salary_min_daily is not None:
            self.salary_min_daily = salary_min_daily
        if salary_max_daily is not None:
            self.salary_max_daily = salary_max_daily

        self.updated_at = datetime.utcnow()

    def to_turnoverit_payload(self, application_base_url: str) -> dict:
        """Convert to Turnover-IT API payload.

        Args:
            application_base_url: Base URL for the application form
                                  (e.g., "https://app.example.com")

        Returns:
            Dictionary payload for Turnover-IT API.
        """
        payload: dict = {
            "reference": self.turnoverit_reference,
            "contract": self.contract_types,
            "title": self.title,
            "description": self.description,
            "qualifications": self.qualifications,
            "status": "PUBLISHED",
        }

        # Location: always use individual fields (key is not supported by API)
        payload["location"] = {
            "locality": self.location_city or "",
            "postalCode": self.location_postal_code or "",
            "county": "",  # Département - not stored separately
            "region": self.location_region or "",
            "country": self.location_country or "France",
        }

        # Optional job details
        if self.skills:
            # Skills should be lowercase slugs for Turnover-IT
            payload["skills"] = [s.lower().replace(" ", "-") for s in self.skills]
        if self.experience_level:
            payload["experienceLevel"] = self.experience_level
        if self.remote:
            payload["remote"] = self.remote
        if self.duration_months:
            payload["durationInMonths"] = self.duration_months
        if self.employer_overview:
            payload["employerOverview"] = self.employer_overview

        # Salary information - always include with explicit nulls
        payload["salary"] = {
            "minAnnual": int(self.salary_min_annual) if self.salary_min_annual else None,
            "maxAnnual": int(self.salary_max_annual) if self.salary_max_annual else None,
            "minDaily": int(self.salary_min_daily) if self.salary_min_daily else None,
            "maxDaily": int(self.salary_max_daily) if self.salary_max_daily else None,
            "currency": "EUR",
        }

        # Application redirect URL - candidates clicking "Apply" on Free-Work
        # will be redirected to our own application form (paid option)
        payload["application"] = {
            "url": f"{application_base_url}/{self.application_token}",
        }

        return payload
