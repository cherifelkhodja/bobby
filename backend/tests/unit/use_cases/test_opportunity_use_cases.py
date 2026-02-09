"""
Tests for Opportunity use cases.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.use_cases.opportunities import (
    ListOpportunitiesUseCase,
    SyncOpportunitiesUseCase,
)
from app.domain.entities import Opportunity


class TestListOpportunitiesUseCase:
    """Tests for ListOpportunitiesUseCase."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_repository, mock_cache):
        return ListOpportunitiesUseCase(mock_repository, mock_cache)

    @pytest.fixture
    def sample_opportunities(self):
        return [
            Opportunity(
                id=uuid4(),
                external_id="OPP-001",
                title="Développeur Python Senior",
                reference="REF-001",
                client_name="Client A",
                description="Mission Python",
                skills=["Python", "FastAPI"],
                is_active=True,
                is_shared=True,
                created_at=datetime.utcnow(),
            ),
            Opportunity(
                id=uuid4(),
                external_id="OPP-002",
                title="Lead Developer Java",
                reference="REF-002",
                client_name="Client B",
                description="Mission Java",
                skills=["Java", "Spring"],
                is_active=True,
                is_shared=True,
                created_at=datetime.utcnow(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_opportunities_success(
        self, use_case, mock_repository, mock_cache, sample_opportunities
    ):
        """Test successful listing of opportunities."""
        mock_cache.get.return_value = None
        mock_repository.list_active.return_value = sample_opportunities
        mock_repository.count_active.return_value = 2

        result = await use_case.execute(page=1, page_size=20)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 20
        mock_repository.list_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_opportunities_with_search(
        self, use_case, mock_repository, mock_cache, sample_opportunities
    ):
        """Test listing with search filter."""
        mock_cache.get.return_value = None
        mock_repository.list_active.return_value = [sample_opportunities[0]]
        mock_repository.count_active.return_value = 1

        result = await use_case.execute(page=1, page_size=20, search="Python")

        assert result.total == 1
        mock_repository.list_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_opportunities_from_cache(
        self, use_case, mock_repository, mock_cache, sample_opportunities
    ):
        """Test listing returns cached result."""
        cached_result = {
            "items": [{"id": str(sample_opportunities[0].id), "title": "Test"}],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        mock_cache.get.return_value = cached_result

        result = await use_case.execute(page=1, page_size=20)

        mock_repository.list_active.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_opportunities_empty(self, use_case, mock_repository, mock_cache):
        """Test listing with no opportunities."""
        mock_cache.get.return_value = None
        mock_repository.list_active.return_value = []
        mock_repository.count_active.return_value = 0

        result = await use_case.execute(page=1, page_size=20)

        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_list_opportunities_pagination(
        self, use_case, mock_repository, mock_cache, sample_opportunities
    ):
        """Test pagination parameters are passed correctly."""
        mock_cache.get.return_value = None
        mock_repository.list_active.return_value = sample_opportunities
        mock_repository.count_active.return_value = 50

        result = await use_case.execute(page=3, page_size=10)

        assert result.page == 3
        assert result.page_size == 10
        mock_repository.list_active.assert_called_with(skip=20, limit=10, search=None)


class TestSyncOpportunitiesUseCase:
    """Tests for SyncOpportunitiesUseCase."""

    @pytest.fixture
    def mock_boond_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_boond_client, mock_repository, mock_cache):
        return SyncOpportunitiesUseCase(mock_boond_client, mock_repository, mock_cache)

    @pytest.fixture
    def boond_opportunities(self):
        return [
            {
                "id": "12345",
                "attributes": {
                    "title": "Mission Python",
                    "reference": "REF-001",
                    "state": 5,
                    "startDate": "2024-01-15",
                    "endDate": "2024-06-15",
                },
            },
            {
                "id": "12346",
                "attributes": {
                    "title": "Mission Java",
                    "reference": "REF-002",
                    "state": 5,
                    "startDate": "2024-02-01",
                    "endDate": "2024-07-01",
                },
            },
        ]

    @pytest.mark.asyncio
    async def test_sync_opportunities_success(
        self, use_case, mock_boond_client, mock_repository, mock_cache, boond_opportunities
    ):
        """Test successful sync from Boond."""
        mock_boond_client.get_opportunities.return_value = boond_opportunities
        mock_repository.get_by_external_id.return_value = None
        mock_repository.save.return_value = MagicMock()

        count = await use_case.execute()

        assert count == 2
        assert mock_repository.save.call_count == 2
        mock_cache.delete.assert_called()

    @pytest.mark.asyncio
    async def test_sync_opportunities_updates_existing(
        self, use_case, mock_boond_client, mock_repository, mock_cache, boond_opportunities
    ):
        """Test sync updates existing opportunities."""
        existing_opp = Opportunity(
            id=uuid4(),
            external_id="12345",
            title="Old Title",
            reference="REF-001",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        mock_boond_client.get_opportunities.return_value = [boond_opportunities[0]]
        mock_repository.get_by_external_id.return_value = existing_opp
        mock_repository.save.return_value = existing_opp

        count = await use_case.execute()

        assert count == 1
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_opportunities_empty(
        self, use_case, mock_boond_client, mock_repository, mock_cache
    ):
        """Test sync with no opportunities from Boond."""
        mock_boond_client.get_opportunities.return_value = []

        count = await use_case.execute()

        assert count == 0
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_opportunities_boond_error(
        self, use_case, mock_boond_client, mock_repository, mock_cache
    ):
        """Test sync handles Boond API error."""
        mock_boond_client.get_opportunities.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            await use_case.execute()

        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sync_clears_cache(
        self, use_case, mock_boond_client, mock_repository, mock_cache, boond_opportunities
    ):
        """Test sync clears the cache after completion."""
        mock_boond_client.get_opportunities.return_value = boond_opportunities
        mock_repository.get_by_external_id.return_value = None
        mock_repository.save.return_value = MagicMock()

        await use_case.execute()

        mock_cache.delete.assert_called()
