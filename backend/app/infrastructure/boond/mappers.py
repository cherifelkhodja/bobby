"""Mappers between BoondManager DTOs and Domain entities."""

from app.domain.entities import Candidate, Opportunity
from app.infrastructure.boond.dtos import BoondOpportunityDTO


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


def map_candidate_to_boond(candidate: Candidate) -> dict:
    """Map domain candidate to BoondManager JSON:API payload.

    BoondManager uses JSON:API format: {"data": {"attributes": {...}}}
    Email field must be "email1" (not "email").
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

    return {
        "data": {
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
