"""BoondManager Data Transfer Objects."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class BoondOpportunityDTO(BaseModel):
    """DTO for BoondManager opportunity data."""

    id: int
    title: str
    reference: str = Field(default="")
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    responseDeadline: Optional[date] = None
    averageDailyRate: Optional[float] = None
    managerFirstName: Optional[str] = None
    managerLastName: Optional[str] = None
    managerEmail: Optional[str] = None
    clientName: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[list[str]] = None
    location: Optional[str] = None
    state: Optional[int] = None

    @property
    def manager_full_name(self) -> Optional[str]:
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
    civility: Optional[str] = None
    phone1: Optional[str] = None
    state: Optional[int] = None


class BoondPositioningDTO(BaseModel):
    """DTO for BoondManager positioning data."""

    id: int
    candidateId: int
    opportunityId: int
    state: Optional[int] = None


class BoondCreateCandidateRequest(BaseModel):
    """Request DTO for creating candidate in BoondManager."""

    firstName: str
    lastName: str
    email: str
    civility: Optional[str] = "M"
    phone1: Optional[str] = None
    state: int = 1


class BoondCreatePositioningRequest(BaseModel):
    """Request DTO for creating positioning in BoondManager."""

    candidate: int  # Candidate ID
    opportunity: int  # Opportunity ID
    state: int = 1
