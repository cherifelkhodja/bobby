"""Unit tests for admin Boond use cases."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.admin.boond import (
    BoondNotConfiguredError,
    GetBoondResourcesUseCase,
    GetBoondStatusUseCase,
    SyncBoondOpportunitiesUseCase,
    TestBoondConnectionUseCase,
)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.BOOND_USERNAME = "test_user"
    settings.BOOND_PASSWORD = "test_pass"
    settings.BOOND_API_URL = "https://api.boondmanager.com"
    return settings


@pytest.fixture
def mock_settings_unconfigured():
    """Create mock settings without Boond credentials."""
    settings = MagicMock()
    settings.BOOND_USERNAME = ""
    settings.BOOND_PASSWORD = ""
    settings.BOOND_API_URL = "https://api.boondmanager.com"
    return settings


@pytest.fixture
def mock_boond_service():
    """Create mock Boond service."""
    return AsyncMock()


@pytest.fixture
def mock_boond_client():
    """Create mock Boond client."""
    return AsyncMock()


@pytest.fixture
def mock_opportunity_repository():
    """Create mock opportunity repository."""
    return AsyncMock()


@pytest.fixture
def mock_cache_service():
    """Create mock cache service."""
    return AsyncMock()


class TestGetBoondStatusUseCase:
    """Tests for GetBoondStatusUseCase."""

    @pytest.mark.asyncio
    async def test_status_configured_connected(
        self, mock_settings, mock_boond_service, mock_opportunity_repository
    ):
        """Test getting status when configured and connected."""
        mock_boond_service.health_check.return_value = True
        mock_opportunity_repository.count_active.return_value = 10
        mock_opportunity_repository.get_last_sync_time.return_value = datetime.utcnow()

        use_case = GetBoondStatusUseCase(
            settings=mock_settings,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
        )
        result = await use_case.execute()

        assert result.connected is True
        assert result.configured is True
        assert result.opportunities_count == 10
        assert result.error is None

    @pytest.mark.asyncio
    async def test_status_not_configured(
        self, mock_settings_unconfigured, mock_boond_service, mock_opportunity_repository
    ):
        """Test getting status when not configured."""
        use_case = GetBoondStatusUseCase(
            settings=mock_settings_unconfigured,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
        )
        result = await use_case.execute()

        assert result.connected is False
        assert result.configured is False
        assert result.error == "BoondManager credentials not configured"

    @pytest.mark.asyncio
    async def test_status_connection_error(
        self, mock_settings, mock_boond_service, mock_opportunity_repository
    ):
        """Test getting status when connection fails."""
        mock_boond_service.health_check.side_effect = Exception("Connection failed")

        use_case = GetBoondStatusUseCase(
            settings=mock_settings,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
        )
        result = await use_case.execute()

        assert result.connected is False
        assert result.configured is True
        assert "Connection failed" in result.error


class TestSyncBoondOpportunitiesUseCase:
    """Tests for SyncBoondOpportunitiesUseCase."""

    @pytest.mark.asyncio
    async def test_sync_not_configured(
        self,
        mock_settings_unconfigured,
        mock_boond_service,
        mock_opportunity_repository,
        mock_cache_service,
    ):
        """Test sync when not configured."""
        use_case = SyncBoondOpportunitiesUseCase(
            settings=mock_settings_unconfigured,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
            cache_service=mock_cache_service,
        )

        with pytest.raises(BoondNotConfiguredError):
            await use_case.execute()

    @pytest.mark.asyncio
    async def test_sync_success(
        self,
        mock_settings,
        mock_boond_service,
        mock_opportunity_repository,
        mock_cache_service,
    ):
        """Test successful sync."""
        # Mock opportunity with external_id
        mock_opp = MagicMock()
        mock_opp.external_id = "123"
        mock_opp.title = "Test Opp"
        mock_boond_service.get_opportunities.return_value = [mock_opp]
        mock_opportunity_repository.get_by_external_id.return_value = None

        use_case = SyncBoondOpportunitiesUseCase(
            settings=mock_settings,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
            cache_service=mock_cache_service,
        )
        result = await use_case.execute()

        assert result.success is True
        assert result.synced_count == 1
        mock_opportunity_repository.save.assert_called_once()
        mock_cache_service.clear_pattern.assert_called_once_with("opportunities:*")

    @pytest.mark.asyncio
    async def test_sync_error(
        self,
        mock_settings,
        mock_boond_service,
        mock_opportunity_repository,
        mock_cache_service,
    ):
        """Test sync with error."""
        mock_boond_service.get_opportunities.side_effect = Exception("API Error")

        use_case = SyncBoondOpportunitiesUseCase(
            settings=mock_settings,
            boond_service=mock_boond_service,
            opportunity_repository=mock_opportunity_repository,
            cache_service=mock_cache_service,
        )
        result = await use_case.execute()

        assert result.success is False
        assert "API Error" in result.message


class TestTestBoondConnectionUseCase:
    """Tests for TestBoondConnectionUseCase."""

    @pytest.mark.asyncio
    async def test_connection_not_configured(
        self, mock_settings_unconfigured, mock_boond_client
    ):
        """Test connection test when not configured."""
        use_case = TestBoondConnectionUseCase(
            settings=mock_settings_unconfigured,
            boond_client=mock_boond_client,
        )
        result = await use_case.execute()

        assert result.success is False
        assert "non configurés" in result.message

    @pytest.mark.asyncio
    async def test_connection_success(self, mock_settings, mock_boond_client):
        """Test successful connection."""
        mock_boond_client.test_connection.return_value = {
            "success": True,
            "status_code": 200,
            "message": "OK",
            "candidates_count": 100,
        }

        use_case = TestBoondConnectionUseCase(
            settings=mock_settings,
            boond_client=mock_boond_client,
        )
        result = await use_case.execute()

        assert result.success is True
        assert result.status_code == 200
        assert result.candidates_count == 100

    @pytest.mark.asyncio
    async def test_connection_failure(self, mock_settings, mock_boond_client):
        """Test failed connection."""
        mock_boond_client.test_connection.return_value = {
            "success": False,
            "status_code": 401,
            "message": "Unauthorized",
        }

        use_case = TestBoondConnectionUseCase(
            settings=mock_settings,
            boond_client=mock_boond_client,
        )
        result = await use_case.execute()

        assert result.success is False
        assert result.status_code == 401


class TestGetBoondResourcesUseCase:
    """Tests for GetBoondResourcesUseCase."""

    @pytest.mark.asyncio
    async def test_resources_not_configured(
        self, mock_settings_unconfigured, mock_boond_client
    ):
        """Test getting resources when not configured."""
        use_case = GetBoondResourcesUseCase(
            settings=mock_settings_unconfigured,
            boond_client=mock_boond_client,
        )

        with pytest.raises(BoondNotConfiguredError):
            await use_case.execute()

    @pytest.mark.asyncio
    async def test_resources_success(self, mock_settings, mock_boond_client):
        """Test getting resources successfully."""
        mock_boond_client.get_resources.return_value = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "+33612345678",
                "manager_id": "2",
                "manager_name": "Jane Manager",
                "agency_id": "1",
                "agency_name": "Paris",
                "resource_type": 1,
                "resource_type_name": "Consultant",
                "state": 1,
                "state_name": "En cours",
                "suggested_role": "user",
            }
        ]

        use_case = GetBoondResourcesUseCase(
            settings=mock_settings,
            boond_client=mock_boond_client,
        )
        result = await use_case.execute()

        assert result.total == 1
        assert len(result.resources) == 1
        assert result.resources[0].first_name == "John"
        assert result.resources[0].email == "john@example.com"

    @pytest.mark.asyncio
    async def test_resources_filters_empty_emails(self, mock_settings, mock_boond_client):
        """Test that resources without emails are filtered out."""
        mock_boond_client.get_resources.return_value = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "suggested_role": "user",
            },
            {
                "id": "2",
                "first_name": "No",
                "last_name": "Email",
                "email": "",  # Empty email
                "suggested_role": "user",
            },
            {
                "id": "3",
                "first_name": "Null",
                "last_name": "Email",
                # No email key
                "suggested_role": "user",
            },
        ]

        use_case = GetBoondResourcesUseCase(
            settings=mock_settings,
            boond_client=mock_boond_client,
        )
        result = await use_case.execute()

        # Should only include the resource with a valid email
        assert result.total == 1
        assert result.resources[0].first_name == "John"
