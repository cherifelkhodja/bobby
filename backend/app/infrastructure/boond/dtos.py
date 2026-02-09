"""BoondManager Data Transfer Objects."""

from datetime import date

from pydantic import BaseModel, Field


class BoondOpportunityDTO(BaseModel):
    """DTO for BoondManager opportunity data."""

    id: int
    title: str
    reference: str = Field(default="")
    startDate: date | None = None
    endDate: date | None = None
    responseDeadline: date | None = None
    averageDailyRate: float | None = None
    managerFirstName: str | None = None
    managerLastName: str | None = None
    managerEmail: str | None = None
    clientName: str | None = None
    description: str | None = None
    skills: list[str] | None = None
    location: str | None = None
    state: int | None = None

    @property
    def manager_full_name(self) -> str | None:
        """Get manager full name."""
        if self.managerFirstName and self.managerLastName:
            return f"{self.managerFirstName} {self.managerLastName}"
        return self.managerFirstName or self.managerLastName


class BoondCandidateDTO(BaseModel):
    """DTO for BoondManager candidate data."""

    id: int
    firstName: str
    lastName: str
    email: str
    civility: str | None = None
    phone1: str | None = None
    state: int | None = None


class BoondPositioningDTO(BaseModel):
    """DTO for BoondManager positioning data."""

    id: int
    candidateId: int
    opportunityId: int
    state: int | None = None


class BoondCreateCandidateRequest(BaseModel):
    """Request DTO for creating candidate in BoondManager."""

    firstName: str
    lastName: str
    email: str
    civility: str | None = "M"
    phone1: str | None = None
    state: int = 1


class BoondCreatePositioningRequest(BaseModel):
    """Request DTO for creating positioning in BoondManager."""

    candidate: int  # Candidate ID
    opportunity: int  # Opportunity ID
    state: int = 1
