"""BoondManager API client with retry and timeout."""

import logging
from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.domain.entities import Candidate, Opportunity
from app.infrastructure.boond.dtos import (
    BoondOpportunityDTO,
)
from app.infrastructure.boond.mappers import (
    BoondAdministrativeData,
    BoondCandidateContext,
    map_boond_opportunity_to_domain,
    map_candidate_administrative_to_boond,
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
    async def get_opportunity(self, external_id: str) -> Opportunity | None:
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
    async def create_candidate(
        self,
        candidate: Candidate,
        context: BoondCandidateContext | None = None,
    ) -> str:
        """Create candidate in BoondManager. Returns external ID."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Creating candidate {candidate.email} in BoondManager")

            payload = map_candidate_to_boond(candidate, context)
            # Set candidate state inside JSON:API attributes
            payload["data"]["attributes"]["state"] = self.candidate_state_id

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
    async def update_candidate_administrative(
        self,
        candidate_id: str,
        admin_data: BoondAdministrativeData,
    ) -> None:
        """Update candidate administrative data (salary, TJM) in BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Updating administrative data for candidate {candidate_id}")

            payload = map_candidate_administrative_to_boond(candidate_id, admin_data)

            response = await client.put(
                f"{self.base_url}/candidates/{candidate_id}/administrative",
                auth=self._auth,
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Updated administrative data for candidate {candidate_id}")

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
                "data": {
                    "attributes": {
                        "state": self.positioning_state_id,
                    },
                    "relationships": {
                        "candidate": {
                            "data": {"id": int(candidate_external_id), "type": "candidate"},
                        },
                        "opportunity": {
                            "data": {"id": int(opportunity_external_id), "type": "opportunity"},
                        },
                    },
                }
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
                    agency_name = (
                        agencies_map.get(agency_id) or self.AGENCY_NAMES.get(agency_id, "")
                        if agency_id
                        else ""
                    )

                    # Get resource type - use hardcoded names
                    resource_type = attrs.get("typeOf", None)
                    resource_type_name = (
                        self.RESOURCE_TYPE_NAMES.get(resource_type, "")
                        if resource_type is not None
                        else ""
                    )

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
                    resource_state_name = (
                        self.RESOURCE_STATE_NAMES.get(resource_state, "")
                        if resource_state is not None
                        else ""
                    )

                    resources.append(
                        {
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
                        }
                    )
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

    # Opportunity states - all states from BoondManager
    OPPORTUNITY_STATE_NAMES = {
        0: "En cours",
        1: "Gagné",
        2: "Perdu",
        3: "Abandonné",
        4: "Gagné attente contrat",
        5: "Piste identifiée",
        6: "Récurrent",
        7: "AO ouvert",
        8: "AO clos",
        9: "Reporté",
        10: "Besoin en avant de phase",
    }

    # Color categories for frontend display
    OPPORTUNITY_STATE_COLORS = {
        0: "blue",  # En cours
        1: "green",  # Gagné
        2: "red",  # Perdu
        3: "gray",  # Abandonné
        4: "green",  # Gagné attente contrat
        5: "yellow",  # Piste identifiée
        6: "green",  # Récurrent
        7: "cyan",  # AO ouvert
        8: "indigo",  # AO clos
        9: "pink",  # Reporté
        10: "blue",  # Besoin en avant de phase
    }

    # States to include when fetching manager opportunities (open/active states only)
    # 0: En cours, 5: Piste identifiée, 6: Récurrent, 7: AO ouvert, 10: Besoin en avant de phase
    ACTIVE_OPPORTUNITY_STATES = [0, 5, 6, 7, 10]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_manager_opportunities(
        self,
        manager_boond_id: str | None = None,
        states: list[int] | None = None,
        fetch_all: bool = False,
    ) -> list[dict]:
        """Fetch opportunities from BoondManager.

        Args:
            manager_boond_id: The BoondManager resource ID of the manager.
                              Required if fetch_all is False.
            states: List of opportunity states to filter. Defaults to ACTIVE_OPPORTUNITY_STATES.
            fetch_all: If True, fetch ALL opportunities (for admin view).

        Returns:
            List of opportunity dicts with id, title, reference, description, etc.
        """
        if not fetch_all and not manager_boond_id:
            raise ValueError("manager_boond_id is required when fetch_all is False")

        if states is None:
            states = self.ACTIVE_OPPORTUNITY_STATES

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            if fetch_all:
                logger.info("Fetching ALL opportunities (admin mode)")
            else:
                logger.info(f"Fetching opportunities for manager {manager_boond_id}")

            all_opportunities = []
            companies_map = {}
            managers_map = {}

            for state in states:
                page = 1
                while True:
                    # Build params
                    params = {
                        "page": page,
                        "maxResults": 500,
                        "opportunityStates": state,
                    }

                    # Only filter by manager if not fetching all
                    if not fetch_all:
                        params["perimeterManagersType"] = "main"
                        params["perimeterManagers"] = manager_boond_id

                    response = await client.get(
                        f"{self.base_url}/opportunities",
                        auth=self._auth,
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()

                    opportunities_batch = data.get("data", [])
                    all_opportunities.extend(opportunities_batch)

                    # Extract company and resource (manager) names from included data
                    for included in data.get("included", []):
                        inc_type = included.get("type")
                        inc_id = str(included.get("id"))
                        inc_attrs = included.get("attributes", {})

                        if inc_type == "company":
                            companies_map[inc_id] = inc_attrs.get("name", "")
                        elif inc_type == "resource":
                            first_name = inc_attrs.get("firstName", "")
                            last_name = inc_attrs.get("lastName", "")
                            managers_map[inc_id] = f"{first_name} {last_name}".strip()

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

                    # Get main manager info
                    main_manager_data = relationships.get("mainManager", {}).get("data")
                    manager_id = str(main_manager_data.get("id")) if main_manager_data else None
                    manager_name = managers_map.get(manager_id, "") if manager_id else ""

                    # Get state
                    opp_state = attrs.get("state", None)
                    opp_state_name = (
                        self.OPPORTUNITY_STATE_NAMES.get(opp_state, "")
                        if opp_state is not None
                        else ""
                    )
                    opp_state_color = (
                        self.OPPORTUNITY_STATE_COLORS.get(opp_state, "gray")
                        if opp_state is not None
                        else "gray"
                    )

                    opportunities.append(
                        {
                            "id": str(item.get("id")),
                            "title": attrs.get("title", ""),
                            "reference": attrs.get("reference", ""),
                            "description": attrs.get("description", ""),
                            "start_date": attrs.get("startDate"),
                            "end_date": attrs.get("endDate"),
                            "company_id": company_id,
                            "company_name": company_name,
                            "manager_id": manager_id,
                            "manager_name": manager_name,
                            "state": opp_state,
                            "state_name": opp_state_name,
                            "state_color": opp_state_color,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse opportunity {item.get('id')}: {e}")

            logger.info(f"Fetched {len(opportunities)} opportunities")
            return opportunities

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_hr_manager_opportunities(
        self,
        hr_manager_boond_id: str,
        states: list[int] | None = None,
    ) -> list[dict]:
        """Fetch opportunities from BoondManager where user is HR manager.

        Args:
            hr_manager_boond_id: The BoondManager resource ID of the HR manager.
            states: List of opportunity states to filter. Defaults to ACTIVE_OPPORTUNITY_STATES.

        Returns:
            List of opportunity dicts with id, title, reference, description, etc.
        """
        if not hr_manager_boond_id:
            raise ValueError("hr_manager_boond_id is required")

        if states is None:
            states = self.ACTIVE_OPPORTUNITY_STATES

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            logger.info(f"Fetching opportunities for HR manager {hr_manager_boond_id}")

            all_opportunities = []
            companies_map = {}
            managers_map = {}

            for state in states:
                page = 1
                while True:
                    # Build params - use perimeterManagersType: "hr" for HR manager filtering
                    params = {
                        "page": page,
                        "maxResults": 500,
                        "opportunityStates": state,
                        "perimeterManagersType": "hr",
                        "perimeterManagers": hr_manager_boond_id,
                    }

                    response = await client.get(
                        f"{self.base_url}/opportunities",
                        auth=self._auth,
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()

                    opportunities_batch = data.get("data", [])
                    all_opportunities.extend(opportunities_batch)

                    # Extract company and resource (manager) names from included data
                    for included in data.get("included", []):
                        inc_type = included.get("type")
                        inc_id = str(included.get("id"))
                        inc_attrs = included.get("attributes", {})

                        if inc_type == "company":
                            companies_map[inc_id] = inc_attrs.get("name", "")
                        elif inc_type == "resource":
                            first_name = inc_attrs.get("firstName", "")
                            last_name = inc_attrs.get("lastName", "")
                            managers_map[inc_id] = f"{first_name} {last_name}".strip()

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

                    # Get main manager info
                    main_manager_data = relationships.get("mainManager", {}).get("data")
                    manager_id = str(main_manager_data.get("id")) if main_manager_data else None
                    manager_name = managers_map.get(manager_id, "") if manager_id else ""

                    # Get HR manager info
                    hr_manager_data = relationships.get("hrManager", {}).get("data")
                    hr_manager_id = str(hr_manager_data.get("id")) if hr_manager_data else None
                    hr_manager_name = managers_map.get(hr_manager_id, "") if hr_manager_id else ""

                    # Get state
                    opp_state = attrs.get("state", None)
                    opp_state_name = (
                        self.OPPORTUNITY_STATE_NAMES.get(opp_state, "")
                        if opp_state is not None
                        else ""
                    )
                    opp_state_color = (
                        self.OPPORTUNITY_STATE_COLORS.get(opp_state, "gray")
                        if opp_state is not None
                        else "gray"
                    )

                    opportunities.append(
                        {
                            "id": str(item.get("id")),
                            "title": attrs.get("title", ""),
                            "reference": attrs.get("reference", ""),
                            "description": attrs.get("description", ""),
                            "start_date": attrs.get("startDate"),
                            "end_date": attrs.get("endDate"),
                            "company_id": company_id,
                            "company_name": company_name,
                            "manager_id": manager_id,
                            "manager_name": manager_name,
                            "hr_manager_id": hr_manager_id,
                            "hr_manager_name": hr_manager_name,
                            "state": opp_state,
                            "state_name": opp_state_name,
                            "state_color": opp_state_color,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse opportunity {item.get('id')}: {e}")

            logger.info(f"Fetched {len(opportunities)} opportunities for HR manager")
            return opportunities

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def get_opportunity_information(self, opportunity_id: str) -> dict:
        """Fetch detailed opportunity information from BoondManager.

        Uses the /opportunities/{id}/information endpoint to get full details
        including description and criteria.

        Args:
            opportunity_id: The BoondManager opportunity ID.

        Returns:
            Dict with full opportunity details including description, criteria,
            company_name, manager_name, etc.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            logger.info(f"Fetching opportunity information for {opportunity_id}")

            response = await client.get(
                f"{self.base_url}/opportunities/{opportunity_id}/information",
                auth=self._auth,
            )
            response.raise_for_status()
            data = response.json()

            opp_data = data.get("data", {})
            attrs = opp_data.get("attributes", {})
            relationships = opp_data.get("relationships", {})

            # Build maps from included data
            companies_map = {}
            managers_map = {}
            contacts_map = {}
            agencies_map = {}

            for included in data.get("included", []):
                inc_type = included.get("type")
                inc_id = str(included.get("id"))
                inc_attrs = included.get("attributes", {})

                if inc_type == "company":
                    companies_map[inc_id] = inc_attrs.get("name", "")
                elif inc_type == "resource":
                    first_name = inc_attrs.get("firstName", "")
                    last_name = inc_attrs.get("lastName", "")
                    managers_map[inc_id] = f"{first_name} {last_name}".strip()
                elif inc_type == "contact":
                    first_name = inc_attrs.get("firstName", "")
                    last_name = inc_attrs.get("lastName", "")
                    contacts_map[inc_id] = f"{first_name} {last_name}".strip()
                elif inc_type == "agency":
                    agencies_map[inc_id] = inc_attrs.get("name", "")

            # Get company info
            company_data = relationships.get("company", {}).get("data")
            company_id = str(company_data.get("id")) if company_data else None
            company_name = companies_map.get(company_id, "") if company_id else ""

            # Get main manager info
            main_manager_data = relationships.get("mainManager", {}).get("data")
            manager_id = str(main_manager_data.get("id")) if main_manager_data else None
            manager_name = managers_map.get(manager_id, "") if manager_id else ""

            # Get contact info
            contact_data = relationships.get("contact", {}).get("data")
            contact_id = str(contact_data.get("id")) if contact_data else None
            contact_name = contacts_map.get(contact_id, "") if contact_id else ""

            # Get agency info
            agency_data = relationships.get("agency", {}).get("data")
            agency_id = str(agency_data.get("id")) if agency_data else None
            agency_name = agencies_map.get(agency_id, "") if agency_id else ""

            # Get state
            opp_state = attrs.get("state", None)
            opp_state_name = (
                self.OPPORTUNITY_STATE_NAMES.get(opp_state, "") if opp_state is not None else ""
            )
            opp_state_color = (
                self.OPPORTUNITY_STATE_COLORS.get(opp_state, "gray")
                if opp_state is not None
                else "gray"
            )

            result = {
                "id": str(opp_data.get("id")),
                "title": attrs.get("title", ""),
                "reference": attrs.get("reference", ""),
                "description": attrs.get("description", ""),
                "criteria": attrs.get("criteria", ""),
                "expertise_area": attrs.get("expertiseArea", ""),
                "place": attrs.get("place", ""),
                "duration": attrs.get("duration"),
                "start_date": attrs.get("startDate"),
                "end_date": attrs.get("closingDate"),  # Use closingDate as end_date
                "closing_date": attrs.get("closingDate"),
                "answer_date": attrs.get("answerDate"),
                "company_id": company_id,
                "company_name": company_name,
                "manager_id": manager_id,
                "manager_name": manager_name,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "agency_id": agency_id,
                "agency_name": agency_name,
                "state": opp_state,
                "state_name": opp_state_name,
                "state_color": opp_state_color,
            }

            logger.info(f"Fetched opportunity information: {result['title']}")
            return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
    )
    async def upload_candidate_cv(
        self,
        candidate_id: str,
        filename: str,
        file_content: bytes,
        content_type: str = "application/pdf",
    ) -> None:
        """Upload CV document to a candidate in BoondManager.

        Uses POST /api/documents with multipart form-data.

        Args:
            candidate_id: The BoondManager candidate ID.
            filename: Original filename of the CV.
            file_content: The CV file content as bytes.
            content_type: MIME type of the file.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            logger.info(f"Uploading CV for candidate {candidate_id}: {filename}")

            response = await client.post(
                f"{self.base_url}/documents",
                auth=self._auth,
                data={
                    "parentType": "candidateResume",
                    "parentId": candidate_id,
                },
                files={
                    "file": (filename, file_content, content_type),
                },
            )
            response.raise_for_status()
            logger.info(f"Uploaded CV for candidate {candidate_id}")

    async def create_candidate_action(
        self,
        candidate_id: str,
        manager_boond_id: str,
        text: str,
        start_date: datetime | None = None,
    ) -> str:
        """Create an action (note) on a candidate in BoondManager.

        No retry: action creation is not idempotent.

        Args:
            candidate_id: The BoondManager candidate ID.
            manager_boond_id: The Boond resource ID of the action's main manager.
            text: HTML-formatted text content for the action.
            start_date: Action date. Defaults to now.

        Returns:
            The created action ID.
        """
        if start_date is None:
            start_date = datetime.now(UTC)

        # Format date as required: YYYY-MM-DDTHH:MM:SS+HHMM
        date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S%z")

        payload = {
            "data": {
                "type": "action",
                "attributes": {
                    "startDate": date_str,
                    "typeOf": 13,
                    "text": text,
                },
                "relationships": {
                    "mainManager": {
                        "data": {
                            "id": manager_boond_id,
                            "type": "resource",
                        }
                    },
                    "dependsOn": {
                        "data": {
                            "id": candidate_id,
                            "type": "candidate",
                        }
                    },
                },
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Creating action for candidate {candidate_id}")

            response = await client.post(
                f"{self.base_url}/actions",
                auth=self._auth,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            # Response data can be a list or a single object
            response_data = data.get("data", {})
            if isinstance(response_data, list):
                action_id = str(response_data[0].get("id", "")) if response_data else ""
            else:
                action_id = str(response_data.get("id", ""))
            logger.info(f"Created action {action_id} for candidate {candidate_id}")
            return action_id
