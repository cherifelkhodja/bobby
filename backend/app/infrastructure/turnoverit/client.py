"""Turnover-IT API client for job posting management."""

import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.domain.exceptions import TurnoverITError

logger = logging.getLogger(__name__)


class TurnoverITClient:
    """Client for Turnover-IT JobConnect API v2.

    This client handles all communication with the Turnover-IT API
    for publishing and managing job offers.

    API Documentation: https://api.turnover-it.com/jobconnect/v2
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize Turnover-IT client.

        Args:
            settings: Application settings containing API credentials.
        """
        self.api_key = settings.TURNOVERIT_API_KEY
        self.base_url = settings.TURNOVERIT_API_URL.rstrip("/")
        self.timeout = httpx.Timeout(10.0)

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/ld+json",
        }

    def _is_configured(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def create_job(self, job_payload: dict[str, Any]) -> str:
        """Create a job posting on Turnover-IT.

        Args:
            job_payload: Job data formatted for Turnover-IT API.
                Required fields: reference, contract, title, description,
                qualifications, location, status.

        Returns:
            The job reference (same as provided in payload).

        Raises:
            TurnoverITError: If API call fails.
        """
        if not self._is_configured():
            raise TurnoverITError("API key not configured")

        reference = job_payload.get("reference", "unknown")
        url = f"{self.base_url}/jobs"
        headers = self._get_headers()

        # Log full request details
        logger.info("=== Turnover-IT CREATE JOB REQUEST ===")
        logger.info(f"URL: POST {url}")
        logger.info(
            f"Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2)}"
        )
        logger.info(f"Payload:\n{json.dumps(job_payload, indent=2, ensure_ascii=False)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=job_payload,
                )

                # Log full response for debugging
                logger.info("=== Turnover-IT RESPONSE ===")
                logger.info(f"Status: {response.status_code}")
                logger.info(f"Body: {response.text}")

                if response.status_code == 201:
                    logger.info(f"Successfully created job: {reference}")
                    return reference

                # Handle error responses
                try:
                    error_data = response.json()
                    if isinstance(error_data.get("message"), list):
                        errors = [e.get("message", str(e)) for e in error_data["message"]]
                        error_msg = "; ".join(errors)
                    else:
                        error_msg = error_data.get("message", response.text)
                except Exception:
                    error_msg = response.text

                logger.error(f"Failed to create job {reference}: {error_msg}")
                raise TurnoverITError(f"Création échouée: {error_msg}")

        except httpx.TimeoutException:
            logger.error(f"Timeout creating job {reference}")
            raise TurnoverITError("Délai d'attente dépassé")
        except httpx.RequestError as e:
            logger.error(f"Request error creating job {reference}: {e}")
            raise TurnoverITError(f"Erreur de connexion: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def update_job(self, reference: str, job_payload: dict[str, Any]) -> bool:
        """Update an existing job posting on Turnover-IT.

        Note: Turnover-IT requires all fields to be sent (no partial updates).

        Args:
            reference: The job reference.
            job_payload: Complete updated job data.

        Returns:
            True if update was successful.

        Raises:
            TurnoverITError: If API call fails.
        """
        if not self._is_configured():
            raise TurnoverITError("API key not configured")

        logger.info(f"Updating job on Turnover-IT: {reference}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/jobs/{reference}",
                    headers=self._get_headers(),
                    json=job_payload,
                )

                if response.status_code == 200:
                    logger.info(f"Successfully updated job: {reference}")
                    return True

                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except Exception:
                    pass

                logger.error(f"Failed to update job {reference}: {error_msg}")
                raise TurnoverITError(f"Mise à jour échouée: {error_msg}")

        except httpx.TimeoutException:
            logger.error(f"Timeout updating job {reference}")
            raise TurnoverITError("Délai d'attente dépassé")
        except httpx.RequestError as e:
            logger.error(f"Request error updating job {reference}: {e}")
            raise TurnoverITError(f"Erreur de connexion: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def close_job(self, reference: str, job_payload: dict[str, Any]) -> bool:
        """Close a job posting on Turnover-IT by setting status to INACTIVE.

        Args:
            reference: The job reference.
            job_payload: The full job payload with status set to INACTIVE.

        Returns:
            True if update was successful.

        Raises:
            TurnoverITError: If API call fails.
        """
        if not self._is_configured():
            raise TurnoverITError("API key not configured")

        # Ensure status is INACTIVE
        job_payload["status"] = "INACTIVE"

        logger.info(f"Closing job on Turnover-IT: {reference}")
        logger.info(f"Payload: {json.dumps(job_payload, indent=2, ensure_ascii=False)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/jobs/{reference}",
                    headers=self._get_headers(),
                    json=job_payload,
                )

                logger.info(f"Response: {response.status_code} - {response.text}")

                if response.status_code == 200:
                    logger.info(f"Successfully closed job: {reference}")
                    return True

                if response.status_code == 404:
                    logger.warning(f"Job not found on Turnover-IT: {reference}")
                    return True  # Consider it closed if not found

                error_msg = response.text
                logger.error(f"Failed to close job {reference}: {error_msg}")
                raise TurnoverITError(f"Fermeture échouée: {error_msg}")

        except httpx.TimeoutException:
            logger.error(f"Timeout closing job {reference}")
            raise TurnoverITError("Délai d'attente dépassé")
        except httpx.RequestError as e:
            logger.error(f"Request error closing job {reference}: {e}")
            raise TurnoverITError(f"Erreur de connexion: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def reactivate_job(self, reference: str, job_payload: dict[str, Any]) -> bool:
        """Reactivate a closed job posting on Turnover-IT by setting status to PUBLISHED.

        Args:
            reference: The job reference.
            job_payload: The full job payload with status set to PUBLISHED.

        Returns:
            True if update was successful.

        Raises:
            TurnoverITError: If API call fails.
        """
        if not self._is_configured():
            raise TurnoverITError("API key not configured")

        # Ensure status is PUBLISHED
        job_payload["status"] = "PUBLISHED"

        logger.info(f"Reactivating job on Turnover-IT: {reference}")
        logger.info(f"Payload: {json.dumps(job_payload, indent=2, ensure_ascii=False)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/jobs/{reference}",
                    headers=self._get_headers(),
                    json=job_payload,
                )

                logger.info(f"Response: {response.status_code} - {response.text}")

                if response.status_code == 200:
                    logger.info(f"Successfully reactivated job: {reference}")
                    return True

                error_msg = response.text
                try:
                    error_data = response.json()
                    if isinstance(error_data.get("message"), list):
                        errors = [e.get("message", str(e)) for e in error_data["message"]]
                        error_msg = "; ".join(errors)
                    else:
                        error_msg = error_data.get("message", error_msg)
                except Exception:
                    pass

                logger.error(f"Failed to reactivate job {reference}: {error_msg}")
                raise TurnoverITError(f"Réactivation échouée: {error_msg}")

        except httpx.TimeoutException:
            logger.error(f"Timeout reactivating job {reference}")
            raise TurnoverITError("Délai d'attente dépassé")
        except httpx.RequestError as e:
            logger.error(f"Request error reactivating job {reference}: {e}")
            raise TurnoverITError(f"Erreur de connexion: {str(e)}")

    async def get_places(self, search: str) -> list[dict[str, Any]]:
        """Get place suggestions from Turnover-IT locations autocomplete API.

        Args:
            search: Search query (city, postal code, region).

        Returns:
            List of places with key, label, locality, region, country, etc.
        """
        if not self._is_configured():
            logger.warning("Turnover-IT API key not configured")
            return []

        if not search or len(search) < 2:
            return []

        try:
            # Locations autocomplete endpoint: https://app.turnover-it.com/api/locations/autocomplete
            locations_url = "https://app.turnover-it.com/api/locations/autocomplete"
            # Use simpler headers for this endpoint (no ld+json)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }

            logger.info(
                f"Turnover-IT locations request: url={locations_url}, "
                f"search={search}, headers={headers}"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    locations_url,
                    headers=headers,
                    params={"search": search},
                )

                logger.info(
                    f"Turnover-IT locations response: "
                    f"status={response.status_code}, body={response.text[:1000]}"
                )

                if response.status_code == 200:
                    places = response.json()
                    # API returns a list directly, not hydra format
                    if isinstance(places, list):
                        return [
                            {
                                "key": place.get("key", ""),
                                "label": place.get("label", ""),
                                "shortLabel": place.get("shortLabel", ""),
                                "locality": place.get("locality") or place.get("adminLevel2", ""),
                                "region": place.get("adminLevel1", ""),
                                "postalCode": place.get("postalCode", ""),
                                "country": place.get("country", ""),
                                "countryCode": place.get("countryCode", ""),
                            }
                            for place in places
                        ]

                # Log error response
                logger.error(
                    f"Turnover-IT locations error: status={response.status_code}, "
                    f"body={response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Failed to fetch places: {e}")
            return []

    async def get_skills(self, search: str | None = None) -> list[dict[str, str]]:
        """Get available skills from Turnover-IT.

        Args:
            search: Optional search query to filter skills.

        Returns:
            List of skills with name and slug.
        """
        if not self._is_configured():
            return []

        try:
            params = {"q": search} if search else {}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url.replace('/v2', '')}/skills",
                    headers=self._get_headers(),
                    params=params,
                )

                if response.status_code == 200:
                    data = response.json()
                    members = data.get("hydra:member", [])
                    return [
                        {"name": skill.get("name", ""), "slug": skill.get("slug", "")}
                        for skill in members
                    ]

                return []

        except Exception as e:
            logger.warning(f"Failed to fetch skills: {e}")
            return []

    async def fetch_all_skills(self) -> list[dict[str, str]]:
        """Fetch all skills from Turnover-IT with pagination.

        Iterates through all pages to get the complete list of skills.

        Returns:
            Complete list of skills with name and slug.
        """
        if not self._is_configured():
            logger.warning("Turnover-IT API key not configured - cannot fetch skills")
            return []

        all_skills: list[dict[str, str]] = []
        page = 1
        max_pages = 50  # Safety limit

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                while page <= max_pages:
                    response = await client.get(
                        f"{self.base_url.replace('/v2', '')}/skills",
                        headers=self._get_headers(),
                        params={"page": page},
                    )

                    if response.status_code != 200:
                        logger.warning(
                            f"Failed to fetch skills page {page}: {response.status_code}"
                        )
                        break

                    data = response.json()
                    members = data.get("hydra:member", [])

                    if not members:
                        break

                    for skill in members:
                        all_skills.append(
                            {
                                "name": skill.get("name", ""),
                                "slug": skill.get("slug", ""),
                            }
                        )

                    # Check if there's a next page
                    view = data.get("hydra:view", {})
                    if "hydra:next" not in view:
                        break

                    page += 1

            logger.info(f"Fetched {len(all_skills)} skills from Turnover-IT ({page} pages)")
            return all_skills

        except Exception as e:
            logger.error(f"Failed to fetch all skills: {e}")
            return all_skills if all_skills else []

    async def health_check(self) -> bool:
        """Check Turnover-IT API availability.

        Returns:
            True if API is available and configured.
        """
        if not self._is_configured():
            logger.warning("Turnover-IT API key not configured")
            return False

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(
                    f"{self.base_url}/jobs/list",
                    headers=self._get_headers(),
                    params={"page": 1},
                )
                # 200 = OK, 404 = no jobs (but API works)
                return response.status_code in (200, 404)

        except Exception as e:
            logger.warning(f"Turnover-IT health check failed: {e}")
            return False

    async def get_job(self, reference: str) -> dict[str, Any] | None:
        """Get a job posting from Turnover-IT.

        Args:
            reference: The job reference.

        Returns:
            Job data or None if not found.
        """
        if not self._is_configured():
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/jobs/{reference}",
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    return response.json()

                return None

        except Exception as e:
            logger.warning(f"Failed to get job {reference}: {e}")
            return None
