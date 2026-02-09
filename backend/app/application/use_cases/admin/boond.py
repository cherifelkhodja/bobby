"""Admin BoondManager use cases."""

from dataclasses import dataclass
from datetime import datetime

from app.config import Settings
from app.domain.ports import BoondServicePort, CacheServicePort, OpportunityRepositoryPort


class BoondNotConfiguredError(Exception):
    """Raised when BoondManager is not configured."""

    pass


@dataclass
class BoondStatusResult:
    """Result of checking Boond status."""

    connected: bool
    configured: bool
    api_url: str
    last_sync: datetime | None = None
    opportunities_count: int = 0
    error: str | None = None


@dataclass
class SyncResult:
    """Result of sync operation."""

    success: bool
    synced_count: int = 0
    message: str = ""


@dataclass
class TestConnectionResult:
    """Result of connection test."""

    success: bool
    status_code: int
    message: str
    candidates_count: int | None = None


@dataclass
class BoondResource:
    """BoondManager resource (employee)."""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    agency_id: str | None = None
    agency_name: str | None = None
    resource_type: int | None = None
    resource_type_name: str | None = None
    state: int | None = None
    state_name: str | None = None
    suggested_role: str = "user"


@dataclass
class BoondResourcesResult:
    """Result of fetching Boond resources."""

    resources: list[BoondResource]
    total: int


class GetBoondStatusUseCase:
    """Use case for getting BoondManager connection status."""

    def __init__(
        self,
        settings: Settings,
        boond_service: BoondServicePort,
        opportunity_repository: OpportunityRepositoryPort,
    ) -> None:
        self._settings = settings
        self._boond_service = boond_service
        self._opportunity_repository = opportunity_repository

    async def execute(self) -> BoondStatusResult:
        """Get BoondManager connection status.

        Returns:
            BoondStatusResult with connection info.
        """
        configured = bool(self._settings.BOOND_USERNAME and self._settings.BOOND_PASSWORD)

        if not configured:
            return BoondStatusResult(
                connected=False,
                configured=False,
                api_url=self._settings.BOOND_API_URL,
                error="BoondManager credentials not configured",
            )

        try:
            connected = await self._boond_service.health_check()
        except Exception as e:
            return BoondStatusResult(
                connected=False,
                configured=True,
                api_url=self._settings.BOOND_API_URL,
                error=str(e),
            )

        # Get opportunities count and last sync time
        count = await self._opportunity_repository.count_active()
        last_sync = await self._opportunity_repository.get_last_sync_time()

        return BoondStatusResult(
            connected=connected,
            configured=True,
            api_url=self._settings.BOOND_API_URL,
            last_sync=last_sync,
            opportunities_count=count,
        )


class SyncBoondOpportunitiesUseCase:
    """Use case for syncing opportunities from BoondManager."""

    def __init__(
        self,
        settings: Settings,
        boond_service: BoondServicePort,
        opportunity_repository: OpportunityRepositoryPort,
        cache_service: CacheServicePort,
    ) -> None:
        self._settings = settings
        self._boond_service = boond_service
        self._opportunity_repository = opportunity_repository
        self._cache_service = cache_service

    async def execute(self) -> SyncResult:
        """Sync opportunities from BoondManager.

        Returns:
            SyncResult with sync info.

        Raises:
            BoondNotConfiguredError: If credentials not configured.
        """
        if not self._settings.BOOND_USERNAME or not self._settings.BOOND_PASSWORD:
            raise BoondNotConfiguredError("BoondManager credentials not configured")

        try:
            # Fetch from BoondManager
            boond_opportunities = await self._boond_service.get_opportunities()

            synced_count = 0
            for boond_opp in boond_opportunities:
                # Check if opportunity already exists
                existing = await self._opportunity_repository.get_by_external_id(
                    boond_opp.external_id
                )

                if existing:
                    # Update existing
                    existing.update_from_sync(
                        title=boond_opp.title,
                        start_date=boond_opp.start_date,
                        end_date=boond_opp.end_date,
                        budget=boond_opp.budget,
                        manager_name=boond_opp.manager_name,
                    )
                    await self._opportunity_repository.save(existing)
                else:
                    # Create new
                    await self._opportunity_repository.save(boond_opp)

                synced_count += 1

            # Invalidate cache
            await self._cache_service.clear_pattern("opportunities:*")

            return SyncResult(
                success=True,
                synced_count=synced_count,
                message=f"{synced_count} opportunités synchronisées",
            )
        except Exception as e:
            return SyncResult(
                success=False,
                synced_count=0,
                message=f"Erreur lors de la synchronisation: {str(e)}",
            )


class TestBoondConnectionUseCase:
    """Use case for testing BoondManager connection."""

    def __init__(
        self,
        settings: Settings,
        boond_client,  # Using concrete type since test_connection is not in port
    ) -> None:
        self._settings = settings
        self._boond_client = boond_client

    async def execute(self) -> TestConnectionResult:
        """Test BoondManager connection.

        Returns:
            TestConnectionResult with connection details.
        """
        if not self._settings.BOOND_USERNAME or not self._settings.BOOND_PASSWORD:
            return TestConnectionResult(
                success=False,
                status_code=0,
                message="Identifiants BoondManager non configurés (BOOND_USERNAME, BOOND_PASSWORD)",
            )

        result = await self._boond_client.test_connection()

        return TestConnectionResult(
            success=result.get("success", False),
            status_code=result.get("status_code", 0),
            message=result.get("message", "Erreur inconnue"),
            candidates_count=result.get("candidates_count"),
        )


class GetBoondResourcesUseCase:
    """Use case for fetching BoondManager resources (employees)."""

    def __init__(
        self,
        settings: Settings,
        boond_client,  # Using concrete type since get_resources is not in port
    ) -> None:
        self._settings = settings
        self._boond_client = boond_client

    async def execute(self) -> BoondResourcesResult:
        """Fetch resources from BoondManager.

        Returns:
            BoondResourcesResult with resources list.

        Raises:
            BoondNotConfiguredError: If credentials not configured.
        """
        if not self._settings.BOOND_USERNAME or not self._settings.BOOND_PASSWORD:
            raise BoondNotConfiguredError("BoondManager credentials not configured")

        resources_data = await self._boond_client.get_resources()

        resources = [
            BoondResource(
                id=r["id"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                email=r["email"],
                phone=r.get("phone"),
                manager_id=r.get("manager_id"),
                manager_name=r.get("manager_name"),
                agency_id=r.get("agency_id"),
                agency_name=r.get("agency_name", ""),
                resource_type=r.get("resource_type"),
                resource_type_name=r.get("resource_type_name"),
                state=r.get("state"),
                state_name=r.get("state_name"),
                suggested_role=r.get("suggested_role", "user"),
            )
            for r in resources_data
            if r.get("email")  # Only include resources with emails
        ]

        return BoondResourcesResult(
            resources=resources,
            total=len(resources),
        )
