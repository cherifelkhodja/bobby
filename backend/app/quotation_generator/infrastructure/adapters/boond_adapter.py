"""BoondManager adapter implementing ERPPort for quotation operations."""

import logging
from datetime import date
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.quotation_generator.domain.entities import Quotation
from app.quotation_generator.domain.exceptions import BoondManagerAPIError
from app.quotation_generator.domain.ports import ERPPort

logger = logging.getLogger(__name__)


class BoondManagerAdapter(ERPPort):
    """BoondManager API adapter for quotation operations.

    This adapter implements the ERPPort interface to create
    quotations in BoondManager and validate entities.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize adapter with settings.

        Args:
            settings: Application settings with BoondManager credentials.
        """
        self.base_url = settings.BOOND_API_URL
        self.timeout = httpx.Timeout(30.0)
        self._auth = (settings.BOOND_USERNAME, settings.BOOND_PASSWORD)
        self._quotation_counter: dict[str, int] = {}

    def _get_client(self) -> httpx.AsyncClient:
        """Create HTTP client with auth and timeout."""
        return httpx.AsyncClient(timeout=self.timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def create_quotation(self, quotation: Quotation) -> tuple[str, str]:
        """Create a quotation in BoondManager.

        Args:
            quotation: The quotation entity to create.

        Returns:
            Tuple of (quotation_id, reference) from BoondManager.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                # Generate quotation number
                number = await self.get_next_quotation_number(
                    quotation.resource_trigramme
                )

                # Build payload
                payload = quotation.to_boond_payload(number)

                logger.info(
                    f"Creating quotation for {quotation.resource_name} "
                    f"on opportunity {quotation.opportunity_id}"
                )

                response = await client.post(
                    f"{self.base_url}/quotations",
                    auth=self._auth,
                    json=payload,
                )

                if response.status_code == 401:
                    raise BoondManagerAPIError(
                        status_code=401,
                        message="Authentication failed",
                    )

                if response.status_code >= 400:
                    error_text = response.text[:500]
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Failed to create quotation: {error_text}",
                    )

                data = response.json()
                quotation_id = str(data.get("data", {}).get("id"))
                reference = data.get("data", {}).get("attributes", {}).get(
                    "reference", number
                )

                logger.info(
                    f"Created quotation {quotation_id} with reference {reference}"
                )
                return quotation_id, reference

            except httpx.RequestError as e:
                logger.error(f"Network error creating quotation: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def validate_opportunity(self, opportunity_id: str) -> bool:
        """Validate that an opportunity exists in BoondManager.

        Args:
            opportunity_id: The opportunity ID to validate (with or without AO prefix).

        Returns:
            True if the opportunity exists and is valid.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        # Remove AO prefix if present
        clean_id = opportunity_id.replace("AO", "")

        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/opportunities/{clean_id}",
                    auth=self._auth,
                )

                if response.status_code == 404:
                    return False

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error validating opportunity: {response.text[:200]}",
                    )

                return True

            except httpx.RequestError as e:
                logger.error(f"Network error validating opportunity: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def validate_resource(self, resource_id: str) -> bool:
        """Validate that a resource exists in BoondManager.

        Args:
            resource_id: The resource ID to validate.

        Returns:
            True if the resource exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/resources/{resource_id}",
                    auth=self._auth,
                )

                if response.status_code == 404:
                    return False

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error validating resource: {response.text[:200]}",
                    )

                return True

            except httpx.RequestError as e:
                logger.error(f"Network error validating resource: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def validate_company(self, company_id: str) -> bool:
        """Validate that a company exists in BoondManager.

        Args:
            company_id: The company ID to validate.

        Returns:
            True if the company exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/companies/{company_id}",
                    auth=self._auth,
                )

                if response.status_code == 404:
                    return False

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error validating company: {response.text[:200]}",
                    )

                return True

            except httpx.RequestError as e:
                logger.error(f"Network error validating company: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def validate_contact(self, contact_id: str) -> bool:
        """Validate that a contact exists in BoondManager.

        Args:
            contact_id: The contact ID to validate.

        Returns:
            True if the contact exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/contacts/{contact_id}",
                    auth=self._auth,
                )

                if response.status_code == 404:
                    return False

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error validating contact: {response.text[:200]}",
                    )

                return True

            except httpx.RequestError as e:
                logger.error(f"Network error validating contact: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    async def get_next_quotation_number(self, prefix: str) -> str:
        """Get the next available quotation number.

        Format: {PREFIX}-{YYYY}{MM}-{NNN}
        Example: DAM-202601-001

        Args:
            prefix: Prefix for the quotation number (e.g., resource trigramme).

        Returns:
            Next available quotation number.
        """
        today = date.today()
        month_key = f"{prefix}-{today.year}{today.month:02d}"

        # Increment counter for this prefix/month combination
        if month_key not in self._quotation_counter:
            self._quotation_counter[month_key] = 0

        self._quotation_counter[month_key] += 1
        counter = self._quotation_counter[month_key]

        return f"{month_key}-{counter:03d}"

    async def reset_counters(self) -> None:
        """Reset quotation number counters.

        Used for testing or when starting a new batch.
        """
        self._quotation_counter.clear()
