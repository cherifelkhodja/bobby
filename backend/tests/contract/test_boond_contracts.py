"""Contract tests for BoondManager DTOs."""

import json
from pathlib import Path

import pytest

from app.infrastructure.boond.dtos import (
    BoondCandidateDTO,
    BoondOpportunityDTO,
)
from app.infrastructure.boond.mappers import map_boond_opportunity_to_domain

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "boond"


def load_fixture(name: str) -> dict:
    """Load JSON fixture file."""
    with open(FIXTURES_PATH / name) as f:
        return json.load(f)


class TestBoondOpportunityContract:
    """Contract tests for BoondManager opportunity responses."""

    def test_should_parse_opportunity_response(self):
        """Verify we can parse a complete opportunity response."""
        payload = load_fixture("opportunity_response.json")
        dto = BoondOpportunityDTO(**payload["data"])

        assert dto.id is not None
        assert dto.title is not None
        assert dto.reference is not None

    def test_should_handle_all_fields(self):
        """Verify all expected fields are present."""
        payload = load_fixture("opportunity_response.json")
        dto = BoondOpportunityDTO(**payload["data"])

        assert dto.id == 12345
        assert dto.title == "Développeur Python Senior"
        assert dto.reference == "REF-2024-001"
        assert dto.averageDailyRate == 600.0
        assert dto.clientName == "Client Entreprise"

    def test_should_handle_missing_optional_fields(self):
        """Verify optional fields default to None."""
        payload = {"id": 1, "title": "Test", "reference": "REF-001"}
        dto = BoondOpportunityDTO(**payload)

        assert dto.startDate is None
        assert dto.endDate is None
        assert dto.averageDailyRate is None
        assert dto.managerFirstName is None

    def test_should_map_to_domain(self):
        """Verify mapping to domain entity works correctly."""
        payload = load_fixture("opportunity_response.json")
        dto = BoondOpportunityDTO(**payload["data"])

        opportunity = map_boond_opportunity_to_domain(dto)

        assert opportunity.external_id == "12345"
        assert opportunity.title == "Développeur Python Senior"
        assert opportunity.budget == 600.0
        assert opportunity.manager_name == "Jean Martin"

    def test_manager_full_name_property(self):
        """Verify manager_full_name combines first and last name."""
        payload = load_fixture("opportunity_response.json")
        dto = BoondOpportunityDTO(**payload["data"])

        assert dto.manager_full_name == "Jean Martin"


class TestBoondCandidateContract:
    """Contract tests for BoondManager candidate responses."""

    def test_should_parse_candidate_response(self):
        """Verify we can parse a complete candidate response."""
        payload = load_fixture("candidate_response.json")
        dto = BoondCandidateDTO(**payload["data"])

        assert dto.firstName is not None
        assert dto.lastName is not None
        assert dto.email is not None

    def test_should_handle_all_fields(self):
        """Verify all expected fields are present."""
        payload = load_fixture("candidate_response.json")
        dto = BoondCandidateDTO(**payload["data"])

        assert dto.id == 67890
        assert dto.firstName == "Pierre"
        assert dto.lastName == "Durand"
        assert dto.email == "pierre.durand@example.com"

    def test_should_handle_missing_optional_fields(self):
        """Verify optional fields default to None."""
        payload = {
            "id": 1,
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
        }
        dto = BoondCandidateDTO(**payload)

        assert dto.civility is None
        assert dto.phone1 is None
        assert dto.state is None
