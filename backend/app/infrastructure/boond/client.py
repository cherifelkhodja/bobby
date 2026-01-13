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
    async def get_resources(self) -> list[dict]:
        """Fetch resources (employees) from BoondManager."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info("Fetching resources from BoondManager")
            response = await client.get(
                f"{self.base_url}/resources",
                auth=self._auth,
                params={"page": 1, "pageSize": 500},
            )
            response.raise_for_status()

            data = response.json()
            resources = []

            for item in data.get("data", []):
                try:
                    attrs = item.get("attributes", {})
                    relationships = item.get("relationships", {})

                    # Get manager ID from relationships
                    manager_data = relationships.get("manager", {}).get("data")
                    manager_id = str(manager_data.get("id")) if manager_data else None

                    resources.append({
                        "id": str(item.get("id")),
                        "first_name": attrs.get("firstName", ""),
                        "last_name": attrs.get("lastName", ""),
                        "email": attrs.get("email1", "") or attrs.get("email2", ""),
                        "manager_id": manager_id,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse resource {item.get('id')}: {e}")

            logger.info(f"Fetched {len(resources)} resources")
            return resources

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
