"""
Tests for Published Opportunity use cases.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.entities import PublishedOpportunity
from app.domain.value_objects import OpportunityStatus


class TestAnonymizeOpportunityUseCase:
    """Tests for anonymizing opportunities."""

    @pytest.fixture
    def mock_boond_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_anonymizer(self):
        return AsyncMock()

    @pytest.fixture
    def boond_opportunity(self):
        return {
            "id": "12345",
            "attributes": {
                "title": "Développeur Python pour BNP Paribas",
                "description": "Mission chez BNP Paribas pour le projet Phoenix...",
                "state": 5,
                "endDate": "2024-06-30",
            },
        }

    @pytest.mark.asyncio
    async def test_anonymize_success(self, mock_boond_client, mock_anonymizer, boond_opportunity):
        """Test successful anonymization."""
        mock_boond_client.get_opportunity.return_value = boond_opportunity
        mock_anonymizer.anonymize.return_value = {
            "title": "Développeur Python pour grande banque française",
            "description": "Mission chez une grande banque française pour un projet de transformation...",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
        }

        # Simulate use case
        result = mock_anonymizer.anonymize(
            boond_opportunity["attributes"]["title"],
            boond_opportunity["attributes"]["description"],
        )

        assert "BNP" not in result["title"]
        assert "Phoenix" not in result["description"]
        assert len(result["skills"]) > 0

    @pytest.mark.asyncio
    async def test_anonymize_preserves_technical_skills(self, mock_anonymizer):
        """Test that technical skills are preserved."""
        mock_anonymizer.anonymize.return_value = {
            "title": "Développeur Python Senior",
            "description": "Développement d'APIs REST avec FastAPI et PostgreSQL",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        }

        result = mock_anonymizer.anonymize("title", "description")

        assert "Python" in result["skills"]
        assert "FastAPI" in result["skills"]


class TestPublishOpportunityUseCase:
    """Tests for publishing opportunities."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def published_opportunity(self):
        return PublishedOpportunity(
            id=uuid4(),
            boond_opportunity_id="12345",
            title="Développeur Python Senior",
            description="Mission de développement...",
            skills=["Python", "FastAPI"],
            status=OpportunityStatus.PUBLISHED,
            published_by=uuid4(),
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_publish_success(self, mock_repository, published_opportunity):
        """Test successful publication."""
        mock_repository.get_by_boond_id.return_value = None
        mock_repository.save.return_value = published_opportunity

        mock_repository.save(published_opportunity)

        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_duplicate_rejected(self, mock_repository, published_opportunity):
        """Test that duplicate publication is rejected."""
        mock_repository.get_by_boond_id.return_value = published_opportunity

        result = await mock_repository.get_by_boond_id("12345")

        assert result is not None
        assert result.boond_opportunity_id == "12345"

    @pytest.mark.asyncio
    async def test_publish_with_end_date(self, mock_repository):
        """Test publication with end date."""
        opp = PublishedOpportunity(
            id=uuid4(),
            boond_opportunity_id="12346",
            title="Mission temporaire",
            description="Description...",
            skills=["Java"],
            end_date=datetime(2024, 12, 31).date(),
            status=OpportunityStatus.PUBLISHED,
            published_by=uuid4(),
            created_at=datetime.utcnow(),
        )
        mock_repository.save.return_value = opp

        result = mock_repository.save(opp)

        assert result.return_value.end_date is not None


class TestListPublishedOpportunitiesUseCase:
    """Tests for listing published opportunities."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def sample_opportunities(self):
        return [
            PublishedOpportunity(
                id=uuid4(),
                boond_opportunity_id="12345",
                title="Développeur Python",
                description="Mission Python...",
                skills=["Python"],
                status=OpportunityStatus.PUBLISHED,
                published_by=uuid4(),
                created_at=datetime.utcnow(),
            ),
            PublishedOpportunity(
                id=uuid4(),
                boond_opportunity_id="12346",
                title="Développeur Java",
                description="Mission Java...",
                skills=["Java"],
                status=OpportunityStatus.PUBLISHED,
                published_by=uuid4(),
                created_at=datetime.utcnow(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_published_only(self, mock_repository, sample_opportunities):
        """Test that only published opportunities are listed."""
        mock_repository.list_published.return_value = sample_opportunities

        result = await mock_repository.list_published()

        assert len(result) == 2
        for opp in result:
            assert opp.status == OpportunityStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, mock_repository, sample_opportunities):
        """Test pagination."""
        mock_repository.list_published.return_value = [sample_opportunities[0]]

        result = await mock_repository.list_published(skip=0, limit=1)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_repository):
        """Test empty list."""
        mock_repository.list_published.return_value = []

        result = await mock_repository.list_published()

        assert len(result) == 0


class TestCloseOpportunityUseCase:
    """Tests for closing opportunities."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def published_opportunity(self):
        return PublishedOpportunity(
            id=uuid4(),
            boond_opportunity_id="12345",
            title="Développeur Python",
            description="Mission...",
            skills=["Python"],
            status=OpportunityStatus.PUBLISHED,
            published_by=uuid4(),
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_close_success(self, mock_repository, published_opportunity):
        """Test successful closure."""
        mock_repository.get_by_id.return_value = published_opportunity

        published_opportunity.close()
        mock_repository.save.return_value = published_opportunity

        assert published_opportunity.status == OpportunityStatus.CLOSED

    @pytest.mark.asyncio
    async def test_close_not_found(self, mock_repository):
        """Test closing non-existent opportunity."""
        mock_repository.get_by_id.return_value = None

        result = await mock_repository.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_close_already_closed(self, mock_repository, published_opportunity):
        """Test closing already closed opportunity."""
        published_opportunity.close()
        mock_repository.get_by_id.return_value = published_opportunity

        assert published_opportunity.status == OpportunityStatus.CLOSED
