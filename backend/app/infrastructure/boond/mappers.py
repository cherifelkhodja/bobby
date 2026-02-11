"""Mappers between BoondManager DTOs and Domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.entities import Candidate, Opportunity
from app.infrastructure.boond.dtos import BoondOpportunityDTO

if TYPE_CHECKING:
    from app.domain.entities.job_application import JobApplication


# Mapping employment_status → BoondManager typeOf
# 0 = Salarié, 1 = Freelance
EMPLOYMENT_STATUS_TO_TYPEOF = {
    "employee": 0,
    "freelance": 1,
    "both": 0,  # Salarié par défaut si les deux
    "freelance,employee": 0,
    "employee,freelance": 0,
}

# Mapping employment_status → BoondManager desiredContract
# 0 = CDI, 3 = Freelance
EMPLOYMENT_STATUS_TO_CONTRACT = {
    "employee": 0,
    "freelance": 3,
    "both": 0,
    "freelance,employee": 0,
    "employee,freelance": 0,
}

# Employment statuses that include employee
_EMPLOYEE_STATUSES = {"employee", "both", "freelance,employee", "employee,freelance"}
# Employment statuses that are freelance only
_FREELANCE_ONLY_STATUSES = {"freelance"}


@dataclass
class BoondCandidateContext:
    """Extra Boond-specific context for candidate creation.

    Contains data that comes from the opportunity and the validating user,
    not from the candidate entity itself.
    """

    employment_status: str | None = None  # freelance, employee, both
    boond_opportunity_id: str | None = None  # For sourceDetail
    hr_manager_boond_id: str | None = None  # User who validates
    main_manager_boond_id: str | None = None  # Opportunity main manager
    agency_boond_id: str | None = None  # Opportunity agency


@dataclass
class BoondAdministrativeData:
    """Administrative data for PUT /candidates/{id}/administrative.

    Maps application salary/TJM fields to Boond administrative attributes.

    Logic per employment_status:
    - employee: salary fields only
    - freelance: TJM fields only
    - both/employee,freelance: salary fields only (TJM is in internalNote)
    """

    salary_current: float | None = None
    salary_desired: float | None = None
    tjm_current: float | None = None
    tjm_desired: float | None = None
    desired_contract: int | None = None  # Boond dictionary integer

    @classmethod
    def from_application(cls, application: JobApplication) -> BoondAdministrativeData:
        """Build admin data from application based on employment status.

        - employee / both: fill salary fields, skip TJM (TJM in internalNote)
        - freelance only: fill TJM fields, skip salary
        """
        status = application.employment_status or ""
        desired_contract = EMPLOYMENT_STATUS_TO_CONTRACT.get(status, 0)

        if status in _FREELANCE_ONLY_STATUSES:
            # Pure freelance: TJM only
            return cls(
                tjm_current=application.tjm_current,
                tjm_desired=application.tjm_desired,
                desired_contract=desired_contract,
            )

        # Employee or both: salary only (TJM info is in internalNote)
        return cls(
            salary_current=application.salary_current,
            salary_desired=application.salary_desired,
            desired_contract=desired_contract,
        )


def map_boond_opportunity_to_domain(dto: BoondOpportunityDTO) -> Opportunity:
    """Map BoondManager opportunity DTO to domain entity."""
    return Opportunity(
        external_id=str(dto.id),
        title=dto.title,
        reference=dto.reference,
        start_date=dto.startDate,
        end_date=dto.endDate,
        response_deadline=dto.responseDeadline,
        budget=dto.averageDailyRate,
        manager_name=dto.manager_full_name,
        manager_email=dto.managerEmail,
        client_name=dto.clientName,
        description=dto.description,
        skills=dto.skills or [],
        location=dto.location,
    )


def map_candidate_to_boond(
    candidate: Candidate,
    context: BoondCandidateContext | None = None,
) -> dict:
    """Map domain candidate to BoondManager JSON:API payload.

    BoondManager uses JSON:API format: {"data": {"attributes": {...}}}
    Email field must be "email1" (not "email").

    Args:
        candidate: The candidate domain entity.
        context: Optional Boond-specific context (typeOf, source, managers, agency).
    """
    attributes: dict = {
        "firstName": candidate.first_name,
        "lastName": candidate.last_name,
        "email1": str(candidate.email),
        "civility": candidate.civility,
    }

    if candidate.phone:
        attributes["phone1"] = str(candidate.phone)

    if candidate.daily_rate is not None:
        attributes["averageDailyPriceForSale"] = candidate.daily_rate

    if candidate.note:
        attributes["internalNote"] = candidate.note

    # Add Boond-specific fields from context
    if context:
        # typeOf: 0=Salarié, 1=Freelance
        if context.employment_status:
            attributes["typeOf"] = EMPLOYMENT_STATUS_TO_TYPEOF.get(
                context.employment_status, 0
            )

        # Source: 6 = Annonce, sourceDetail = Boond opportunity ID
        attributes["source"] = 6
        if context.boond_opportunity_id:
            attributes["sourceDetail"] = context.boond_opportunity_id

    # Build relationships
    relationships: dict = {}
    if context:
        if context.hr_manager_boond_id:
            relationships["hrManager"] = {
                "data": {"id": int(context.hr_manager_boond_id), "type": "resource"}
            }
        if context.main_manager_boond_id:
            relationships["mainManager"] = {
                "data": {"id": int(context.main_manager_boond_id), "type": "resource"}
            }
        if context.agency_boond_id:
            relationships["agency"] = {
                "data": {"id": int(context.agency_boond_id), "type": "agency"}
            }

    payload: dict = {
        "data": {
            "attributes": attributes,
        }
    }

    if relationships:
        payload["data"]["relationships"] = relationships

    return payload


def map_candidate_administrative_to_boond(
    candidate_id: str,
    admin_data: BoondAdministrativeData,
) -> dict:
    """Map administrative data to BoondManager PUT /candidates/{id}/administrative payload.

    Populates salary (actualSalary, desiredSalary) and TJM (actualAverageDailyCost,
    desiredAverageDailyCost) based on the application data.
    """
    attributes: dict = {}

    if admin_data.salary_current is not None:
        attributes["actualSalary"] = admin_data.salary_current

    if admin_data.salary_desired is not None or admin_data.salary_current is not None:
        attributes["desiredSalary"] = {
            "min": admin_data.salary_current or admin_data.salary_desired,
            "max": admin_data.salary_desired or admin_data.salary_current,
        }

    if admin_data.tjm_current is not None:
        attributes["actualAverageDailyCost"] = admin_data.tjm_current

    if admin_data.tjm_desired is not None or admin_data.tjm_current is not None:
        attributes["desiredAverageDailyCost"] = {
            "min": admin_data.tjm_current or admin_data.tjm_desired,
            "max": admin_data.tjm_desired or admin_data.tjm_current,
        }

    if admin_data.desired_contract is not None:
        attributes["desiredContract"] = admin_data.desired_contract

    return {
        "data": {
            "id": candidate_id,
            "type": "candidate",
            "attributes": attributes,
        }
    }


def map_opportunity_to_read_model(opportunity: Opportunity) -> dict:
    """Map opportunity to dictionary for caching."""
    return {
        "id": str(opportunity.id),
        "external_id": opportunity.external_id,
        "title": opportunity.title,
        "reference": opportunity.reference,
        "start_date": opportunity.start_date.isoformat() if opportunity.start_date else None,
        "end_date": opportunity.end_date.isoformat() if opportunity.end_date else None,
        "response_deadline": (
            opportunity.response_deadline.isoformat() if opportunity.response_deadline else None
        ),
        "budget": opportunity.budget,
        "manager_name": opportunity.manager_name,
        "client_name": opportunity.client_name,
        "is_active": opportunity.is_active,
    }
