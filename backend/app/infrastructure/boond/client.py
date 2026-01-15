"""BoondManager API client with retry and timeout."""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.domain.entities import Candidate, Opportunity
from app.infrastructure.boond.dtos import (
    BoondCandidateDTO,
    BoondOpportunityDTO,
    BoondPositioningDTO,
)
from app.infrastructure.boond.mappers import (
    map_boond_opportunity_to_domain,
    map_candidate_to_boond,
)

logger = logging.getLogger(__name__)


class BoondClient:
    """BoondManager API client."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.BOOND_API_URL
        self.timeout = httpx.Timeout(5.0)
        self._auth = (settings.BOOND_USERNAME, settings.BOOND_PASSWORD)
        self.candidate_state_id = settings.BOOND_CANDIDATE_STATE_ID
        self.positioning_state_id = settings.BOOND_POSITIONING_STATE_ID

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_opportunities(self) -> list[Opportunity]:
        """Fetch opportunities from BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info("Fetching opportunities from BoondManager")
            response = await client.get(
                f"{self.base_url}/opportunities",
                auth=self._auth,
            )
            response.raise_for_status()

            data = response.json()
            opportunities = []

            for item in data.get("data", []):
                try:
                    dto = BoondOpportunityDTO(**item)
                    opportunities.append(map_boond_opportunity_to_domain(dto))
                except Exception as e:
                    logger.warning(f"Failed to parse opportunity {item.get('id')}: {e}")

            logger.info(f"Fetched {len(opportunities)} opportunities")
            return opportunities

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_opportunity(self, external_id: str) -> Optional[Opportunity]:
        """Fetch single opportunity from BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Fetching opportunity {external_id} from BoondManager")
            response = await client.get(
                f"{self.base_url}/opportunities/{external_id}",
                auth=self._auth,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            dto = BoondOpportunityDTO(**data.get("data", {}))
            return map_boond_opportunity_to_domain(dto)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def create_candidate(self, candidate: Candidate) -> str:
        """Create candidate in BoondManager. Returns external ID."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Creating candidate {candidate.email} in BoondManager")

            payload = map_candidate_to_boond(candidate)
            payload["state"] = self.candidate_state_id

            response = await client.post(
                f"{self.base_url}/candidates",
                auth=self._auth,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            external_id = str(data.get("data", {}).get("id"))
            logger.info(f"Created candidate with ID {external_id}")
            return external_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def create_positioning(
        self,
        candidate_external_id: str,
        opportunity_external_id: str,
    ) -> str:
        """Create positioning in BoondManager. Returns positioning ID."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(
                f"Creating positioning for candidate {candidate_external_id} "
                f"on opportunity {opportunity_external_id}"
            )

            payload = {
                "candidate": int(candidate_external_id),
                "opportunity": int(opportunity_external_id),
                "state": self.positioning_state_id,
            }

            response = await client.post(
                f"{self.base_url}/positionings",
                auth=self._auth,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            positioning_id = str(data.get("data", {}).get("id"))
            logger.info(f"Created positioning with ID {positioning_id}")
            return positioning_id

    async def health_check(self) -> bool:
        """Check BoondManager API availability using GET /candidates."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(
                    f"{self.base_url}/candidates",
                    auth=self._auth,
                    params={"page": 1, "pageSize": 1},
                )
                logger.info(f"BoondManager health check: status={response.status_code}")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"BoondManager health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_resource_types(self) -> dict[int, str]:
        """Fetch resource types dictionary from BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info("Fetching resource types dictionary from BoondManager")
            response = await client.get(
                f"{self.base_url}/application/dictionary/setting.typeOf.resource",
                auth=self._auth,
            )
            response.raise_for_status()

            data = response.json()
            types_dict = {}

            for item in data.get("data", []):
                try:
                    type_id = int(item.get("id"))
                    type_name = item.get("attributes", {}).get("value", "")
                    types_dict[type_id] = type_name
                except Exception as e:
                    logger.warning(f"Failed to parse resource type {item.get('id')}: {e}")

            logger.info(f"Fetched {len(types_dict)} resource types")
            return types_dict

    # Hardcoded resource type names to avoid extra API call
    # Types 0, 1, 10 are all Consultant
    RESOURCE_TYPE_NAMES = {
        0: "Consultant",
        1: "Consultant",
        2: "Commercial",
        5: "RH",
        6: "Direction RH",
        10: "Consultant",
    }

    # Hardcoded agency names as fallback
    AGENCY_NAMES = {
        "1": "Gemini",
        "5": "Craftmania",
    }

    # Hardcoded resource state names
    RESOURCE_STATE_NAMES = {
        0: "Sortie",
        1: "En cours",
        2: "Intercontrat",
        3: "Arrivée prochaine",
        7: "Sortie prochaine",
    }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_resources(self) -> list[dict]:
        """Fetch resources (employees) from BoondManager.

        Returns resources with all states (0, 1, 2, 3, 7).
        Uses included data for agencies to avoid extra API calls.
        Handles pagination to fetch all resources.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            logger.info("Fetching resources from BoondManager")

            # Fetch resources with all states
            all_resources = []
            agencies_map = {}
            managers_map = {}  # Map manager_id -> "FirstName LastName"

            for state in [0, 1, 2, 3, 7]:
                page = 1
                while True:
                    response = await client.get(
                        f"{self.base_url}/resources",
                        auth=self._auth,
                        params={"page": page, "maxResults": 500, "resourceStates": state},
                    )
                    response.raise_for_status()
                    data = response.json()
                    resources_batch = data.get("data", [])
                    all_resources.extend(resources_batch)

                    # Extract agencies and managers from included data
                    for included in data.get("included", []):
                        if included.get("type") == "agency":
                            agency_id = str(included.get("id"))
                            agency_name = included.get("attributes", {}).get("name", "")
                            agencies_map[agency_id] = agency_name
                        elif included.get("type") == "resource":
                            # Manager info from included
                            manager_id = str(included.get("id"))
                            attrs = included.get("attributes", {})
                            first_name = attrs.get("firstName", "")
                            last_name = attrs.get("lastName", "")
                            if first_name or last_name:
                                managers_map[manager_id] = f"{first_name} {last_name}".strip()

                    # Check for more pages
                    meta = data.get("meta", {})
                    total_pages = meta.get("totalPages", 1)
                    if page >= total_pages:
                        break
                    page += 1

            resources = []
            for item in all_resources:
                try:
                    attrs = item.get("attributes", {})
                    relationships = item.get("relationships", {})

                    # Get manager ID from relationships (mainManager in Boond API)
                    manager_data = relationships.get("mainManager", {}).get("data")
                    manager_id = str(manager_data.get("id")) if manager_data else None

                    # Get agency from relationships
                    agency_data = relationships.get("agency", {}).get("data")
                    agency_id = str(agency_data.get("id")) if agency_data else None
                    # Use included data first, fallback to hardcoded names
                    agency_name = agencies_map.get(agency_id) or self.AGENCY_NAMES.get(agency_id, "") if agency_id else ""

                    # Get resource type - use hardcoded names
                    resource_type = attrs.get("typeOf", None)
                    resource_type_name = self.RESOURCE_TYPE_NAMES.get(resource_type, "") if resource_type is not None else ""

                    # Determine role based on type
                    # 0, 1, 10 -> user (Consultant)
                    # 2 -> commercial
                    # 5, 6 -> rh (RH, Direction RH)
                    if resource_type in [0, 1, 10]:
                        suggested_role = "user"
                    elif resource_type == 2:
                        suggested_role = "commercial"
                    elif resource_type in [5, 6]:
                        suggested_role = "rh"
                    else:
                        suggested_role = "user"

                    # Get phone number (mobile or phone1)
                    phone = attrs.get("mobile", "") or attrs.get("phone1", "")

                    # Get manager name from included data
                    manager_name = managers_map.get(manager_id, "") if manager_id else ""

                    # Get resource state
                    resource_state = attrs.get("state", None)
                    resource_state_name = self.RESOURCE_STATE_NAMES.get(resource_state, "") if resource_state is not None else ""

                    resources.append({
                        "id": str(item.get("id")),
                        "first_name": attrs.get("firstName", ""),
                        "last_name": attrs.get("lastName", ""),
                        "email": attrs.get("email1", "") or attrs.get("email2", ""),
                        "phone": phone,
                        "manager_id": manager_id,
                        "manager_name": manager_name,
                        "agency_id": agency_id,
                        "agency_name": agency_name,
                        "resource_type": resource_type,
                        "resource_type_name": resource_type_name,
                        "state": resource_state,
                        "state_name": resource_state_name,
                        "suggested_role": suggested_role,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse resource {item.get('id')}: {e}")

            logger.info(f"Fetched {len(resources)} resources")
            return resources

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_agencies(self) -> dict[str, str]:
        """Fetch agencies dictionary from BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info("Fetching agencies from BoondManager")
            response = await client.get(
                f"{self.base_url}/agencies",
                auth=self._auth,
                params={"page": 1, "pageSize": 100},
            )
            response.raise_for_status()

            data = response.json()
            agencies = {}

            for item in data.get("data", []):
                try:
                    agency_id = str(item.get("id"))
                    agency_name = item.get("attributes", {}).get("name", "")
                    agencies[agency_id] = agency_name
                except Exception as e:
                    logger.warning(f"Failed to parse agency {item.get('id')}: {e}")

            logger.info(f"Fetched {len(agencies)} agencies")
            return agencies

    async def test_connection(self) -> dict:
        """Test connection and return detailed info."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(
                    f"{self.base_url}/candidates",
                    auth=self._auth,
                    params={"page": 1, "pageSize": 1},
                )

                if response.status_code == 200:
                    data = response.json()
                    total = data.get("numberOfResources", 0)
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "message": f"Connexion reussie. {total} candidats dans BoondManager.",
                        "candidates_count": total,
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "message": "Authentification echouee. Verifiez vos identifiants.",
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "message": f"Erreur HTTP {response.status_code}: {response.text[:200]}",
                    }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "status_code": 0,
                "message": f"Impossible de se connecter a l'API: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "message": f"Erreur: {str(e)}",
            }

    # Opportunity states for filtering
    # 0: Perdue, 5: En cours, 6: Signée, 7: Abandonnée, 10: En attente
    OPPORTUNITY_STATE_NAMES = {
        0: "Perdue",
        5: "En cours",
        6: "Signée",
        7: "Abandonnée",
        10: "En attente",
    }

    # States to include when fetching manager opportunities (active states)
    ACTIVE_OPPORTUNITY_STATES = [0, 5, 6, 7, 10]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_manager_opportunities(
        self,
        manager_boond_id: str,
        states: Optional[list[int]] = None,
    ) -> list[dict]:
        """Fetch opportunities where the user is the main manager.

        Args:
            manager_boond_id: The BoondManager resource ID of the manager.
            states: List of opportunity states to filter. Defaults to ACTIVE_OPPORTUNITY_STATES.

        Returns:
            List of opportunity dicts with id, title, reference, description, etc.
        """
        if states is None:
            states = self.ACTIVE_OPPORTUNITY_STATES

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            logger.info(f"Fetching opportunities for manager {manager_boond_id}")

            all_opportunities = []
            companies_map = {}

            for state in states:
                page = 1
                while True:
                    response = await client.get(
                        f"{self.base_url}/opportunities",
                        auth=self._auth,
                        params={
                            "page": page,
                            "maxResults": 500,
                            "perimeterManagersType": "main",
                            "perimeterManagers": manager_boond_id,
                            "opportunitiesStates": state,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    opportunities_batch = data.get("data", [])
                    all_opportunities.extend(opportunities_batch)

                    # Extract company names from included data
                    for included in data.get("included", []):
                        if included.get("type") == "company":
                            company_id = str(included.get("id"))
                            company_name = included.get("attributes", {}).get("name", "")
                            companies_map[company_id] = company_name

                    # Check for more pages
                    meta = data.get("meta", {})
                    total_pages = meta.get("totalPages", 1)
                    if page >= total_pages:
                        break
                    page += 1

            opportunities = []
            for item in all_opportunities:
                try:
                    attrs = item.get("attributes", {})
                    relationships = item.get("relationships", {})

                    # Get company info
                    company_data = relationships.get("company", {}).get("data")
                    company_id = str(company_data.get("id")) if company_data else None
                    company_name = companies_map.get(company_id, "") if company_id else ""

                    # Get state
                    opp_state = attrs.get("state", None)
                    opp_state_name = self.OPPORTUNITY_STATE_NAMES.get(opp_state, "") if opp_state is not None else ""

                    opportunities.append({
                        "id": str(item.get("id")),
                        "title": attrs.get("title", ""),
                        "reference": attrs.get("reference", ""),
                        "description": attrs.get("description", ""),
                        "start_date": attrs.get("startDate"),
                        "end_date": attrs.get("endDate"),
                        "company_id": company_id,
                        "company_name": company_name,
                        "state": opp_state,
                        "state_name": opp_state_name,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse opportunity {item.get('id')}: {e}")

            logger.info(f"Fetched {len(opportunities)} opportunities for manager {manager_boond_id}")
            return opportunities
