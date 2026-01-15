"""BoondManager enrichment service for quotation data."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings

logger = logging.getLogger(__name__)


# Thales company IDs and their billing detail IDs
THALES_COMPANY_IDS = {"228", "31", "65"}

COMPANY_DETAIL_MAPPING = {
    "228": "37",
    "31": "14",
    "65": "27",
}


@dataclass
class ResourceInfo:
    """Resource information from BoondManager."""

    id: str
    first_name: str
    last_name: str
    trigramme: str
    email: str


@dataclass
class ProjectInfo:
    """Project information from BoondManager."""

    id: str
    reference: str
    opportunity_id: str
    opportunity_title: str
    company_id: str
    company_name: str
    company_detail_id: str
    contact_id: str
    contact_name: str


@dataclass
class EnrichedQuotationData:
    """Enriched quotation data from BoondManager."""

    resource_id: str
    resource_name: str
    resource_trigramme: str
    opportunity_id: str
    company_id: str
    company_name: str
    company_detail_id: str
    contact_id: str
    contact_name: str


class BoondEnrichmentService:
    """Service for enriching quotation data from BoondManager.

    This service:
    1. Searches for resources by name
    2. Gets their Thales projects
    3. Returns the latest project's data for quotation creation
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize with settings."""
        self.base_url = settings.BOOND_API_URL
        self.timeout = httpx.Timeout(30.0)
        self._auth = (settings.BOOND_USERNAME, settings.BOOND_PASSWORD)

    def _get_client(self) -> httpx.AsyncClient:
        """Create HTTP client."""
        return httpx.AsyncClient(timeout=self.timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def search_resource_by_name(
        self, first_name: str, last_name: str
    ) -> Optional[ResourceInfo]:
        """Search for a resource by first and last name.

        Args:
            first_name: Resource first name.
            last_name: Resource last name.

        Returns:
            ResourceInfo if found, None otherwise.
        """
        async with self._get_client() as client:
            logger.info(f"Searching for resource: {first_name} {last_name}")

            # Search using keywords parameter
            search_term = f"{first_name} {last_name}"
            response = await client.get(
                f"{self.base_url}/resources",
                auth=self._auth,
                params={
                    "keywords": search_term,
                    "maxResults": 50,
                },
            )
            response.raise_for_status()

            data = response.json()
            resources = data.get("data", [])

            # Find exact match (case-insensitive)
            first_lower = first_name.lower().strip()
            last_lower = last_name.lower().strip()

            for resource in resources:
                attrs = resource.get("attributes", {})
                res_first = attrs.get("firstName", "").lower().strip()
                res_last = attrs.get("lastName", "").lower().strip()

                if res_first == first_lower and res_last == last_lower:
                    # Build trigramme from initials
                    trigramme = self._build_trigramme(
                        attrs.get("firstName", ""),
                        attrs.get("lastName", "")
                    )

                    return ResourceInfo(
                        id=str(resource.get("id")),
                        first_name=attrs.get("firstName", ""),
                        last_name=attrs.get("lastName", ""),
                        trigramme=trigramme,
                        email=attrs.get("email1", "") or attrs.get("email2", ""),
                    )

            logger.warning(f"Resource not found: {first_name} {last_name}")
            return None

    def _build_trigramme(self, first_name: str, last_name: str) -> str:
        """Build trigramme from name (e.g., Raphael COLLARD -> RCO)."""
        if not first_name or not last_name:
            return "XXX"

        # First letter of first name + first two letters of last name
        tri = first_name[0].upper() + last_name[:2].upper()
        return tri

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def get_resource_thales_projects(
        self, resource_id: str
    ) -> list[ProjectInfo]:
        """Get Thales projects for a resource.

        Args:
            resource_id: BoondManager resource ID.

        Returns:
            List of ProjectInfo for Thales companies only.
        """
        async with self._get_client() as client:
            logger.info(f"Fetching projects for resource {resource_id}")

            response = await client.get(
                f"{self.base_url}/resources/{resource_id}/projects",
                auth=self._auth,
            )
            response.raise_for_status()

            data = response.json()
            projects_data = data.get("data", [])
            included = data.get("included", [])

            # Build lookup maps from included data
            contacts_map = {}
            companies_map = {}
            opportunities_map = {}

            for item in included:
                item_type = item.get("type")
                item_id = str(item.get("id"))
                attrs = item.get("attributes", {})

                if item_type == "contact":
                    contacts_map[item_id] = {
                        "name": f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
                    }
                elif item_type == "company":
                    companies_map[item_id] = {
                        "name": attrs.get("name", ""),
                    }
                elif item_type == "opportunity":
                    opportunities_map[item_id] = {
                        "title": attrs.get("title", ""),
                    }

            # Filter and map projects
            projects = []
            for project in projects_data:
                relationships = project.get("relationships", {})

                # Get company ID
                company_data = relationships.get("company", {}).get("data")
                company_id = str(company_data.get("id")) if company_data else None

                # Filter: only Thales companies
                if company_id not in THALES_COMPANY_IDS:
                    continue

                # Get other IDs
                contact_data = relationships.get("contact", {}).get("data")
                contact_id = str(contact_data.get("id")) if contact_data else None

                opportunity_data = relationships.get("opportunity", {}).get("data")
                opportunity_id = str(opportunity_data.get("id")) if opportunity_data else None

                # Get names from included data
                company_name = companies_map.get(company_id, {}).get("name", "")
                contact_name = contacts_map.get(contact_id, {}).get("name", "")
                opportunity_title = opportunities_map.get(opportunity_id, {}).get("title", "")

                # Get company_detail_id from mapping
                company_detail_id = COMPANY_DETAIL_MAPPING.get(company_id, company_id)

                projects.append(ProjectInfo(
                    id=str(project.get("id")),
                    reference=project.get("attributes", {}).get("reference", ""),
                    opportunity_id=opportunity_id or "",
                    opportunity_title=opportunity_title,
                    company_id=company_id,
                    company_name=company_name,
                    company_detail_id=company_detail_id,
                    contact_id=contact_id or "",
                    contact_name=contact_name,
                ))

            logger.info(f"Found {len(projects)} Thales projects for resource {resource_id}")
            return projects

    async def get_latest_thales_project(
        self, resource_id: str
    ) -> Optional[ProjectInfo]:
        """Get the latest Thales project for a resource.

        Args:
            resource_id: BoondManager resource ID.

        Returns:
            Latest ProjectInfo or None if no Thales projects.
        """
        projects = await self.get_resource_thales_projects(resource_id)

        if not projects:
            return None

        # Return the first one (API returns most recent first)
        # If needed, we can add date-based sorting later
        return projects[0]

    async def enrich_quotation_data(
        self, first_name: str, last_name: str
    ) -> Optional[EnrichedQuotationData]:
        """Enrich quotation data by fetching from BoondManager.

        This method:
        1. Searches for the resource by name
        2. Gets their latest Thales project
        3. Returns all the IDs needed for quotation creation

        Args:
            first_name: Resource first name.
            last_name: Resource last name.

        Returns:
            EnrichedQuotationData if successful, None otherwise.
        """
        # Step 1: Find resource
        resource = await self.search_resource_by_name(first_name, last_name)
        if not resource:
            logger.error(f"Resource not found: {first_name} {last_name}")
            return None

        # Step 2: Get latest Thales project
        project = await self.get_latest_thales_project(resource.id)
        if not project:
            logger.error(f"No Thales project found for resource {resource.id}")
            return None

        # Step 3: Build enriched data
        return EnrichedQuotationData(
            resource_id=resource.id,
            resource_name=f"{resource.first_name} {resource.last_name}",
            resource_trigramme=resource.trigramme,
            opportunity_id=project.opportunity_id,
            company_id=project.company_id,
            company_name=project.company_name,
            company_detail_id=project.company_detail_id,
            contact_id=project.contact_id,
            contact_name=project.contact_name,
        )
