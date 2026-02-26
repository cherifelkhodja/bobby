"""BoondManager adapter implementing ERPPort for quotation operations."""

import json
import logging
from datetime import date

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

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

    @staticmethod
    def _is_retryable_error(exception: BaseException) -> bool:
        """Check if an error should be retried (skip 4xx client errors)."""
        if isinstance(exception, BoondManagerAPIError):
            return exception.status_code == 0 or exception.status_code >= 500
        return isinstance(exception, httpx.RequestError)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_is_retryable_error),
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
                # Build payload (uses need_title as number, period.start_date as date)
                payload = quotation.to_boond_payload()

                logger.info(
                    f"Creating quotation for {quotation.resource_name} "
                    f"on opportunity {quotation.opportunity_id}"
                )
                logger.debug(
                    f"Quotation payload: {json.dumps(payload, indent=2, ensure_ascii=False)}"
                )

                response = await client.post(
                    f"{self.base_url}/apps/quotations/quotations",
                    auth=self._auth,
                    json=payload,
                )

                if response.status_code == 401:
                    raise BoondManagerAPIError(
                        status_code=401,
                        message="Authentication failed",
                    )

                if response.status_code >= 400:
                    logger.error(
                        f"BoondManager quotation creation failed ({response.status_code}).\n"
                        f"Sent payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n"
                        f"Full response: {response.text}"
                    )
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Failed to create quotation: {response.text[:2000]}",
                    )

                data = response.json()
                quotation_id = str(data.get("data", {}).get("id"))
                reference = (
                    data.get("data", {})
                    .get("attributes", {})
                    .get("reference", quotation.need_title)
                )

                logger.info(f"Created quotation {quotation_id} with reference {reference}")
                return quotation_id, reference

            except httpx.RequestError as e:
                logger.error(f"Network error creating quotation: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e

    async def get_quotation(self, quotation_id: str) -> dict:
        """Get a quotation from BoondManager (for debugging format).

        Args:
            quotation_id: The BoondManager quotation ID.

        Returns:
            Raw JSON response from BoondManager.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/apps/quotations/quotations/{quotation_id}",
                    auth=self._auth,
                )

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error fetching quotation: {response.text[:500]}",
                    )

                return response.json()

            except httpx.RequestError as e:
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
    async def get_opportunity_title(self, opportunity_id: str) -> str:
        """Get the title of an opportunity from BoondManager.

        Args:
            opportunity_id: The opportunity ID (with or without AO prefix).

        Returns:
            The opportunity title (titre du besoin).

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
                    logger.warning(f"Opportunity {clean_id} not found")
                    return ""

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error fetching opportunity: {response.text[:200]}",
                    )

                data = response.json()
                title = data.get("data", {}).get("attributes", {}).get("title", "")
                return title

            except httpx.RequestError as e:
                logger.error(f"Network error fetching opportunity title: {e}")
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def get_company_contacts(self, company_id: str) -> list[dict]:
        """Get contacts for a company from BoondManager.

        Uses /contacts?keywords=CSOCid_company endpoint.

        Args:
            company_id: The company ID.

        Returns:
            List of contacts with id and name.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        async with self._get_client() as client:
            try:
                # Search contacts by company ID using CSOC prefix
                response = await client.get(
                    f"{self.base_url}/contacts",
                    auth=self._auth,
                    params={
                        "keywords": f"CSOC{company_id}",
                        "maxResults": 500,
                    },
                )

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error fetching company contacts: {response.text[:200]}",
                    )

                data = response.json()
                contacts = []

                for contact in data.get("data", []):
                    attrs = contact.get("attributes", {})
                    first_name = attrs.get("firstName", "")
                    last_name = attrs.get("lastName", "")
                    name = f"{first_name} {last_name}".strip()

                    contacts.append(
                        {
                            "id": str(contact.get("id")),
                            "name": name or f"Contact {contact.get('id')}",
                        }
                    )

                logger.info(f"Found {len(contacts)} contacts for company {company_id}")
                return contacts

            except httpx.RequestError as e:
                logger.error(f"Network error fetching company contacts: {e}")
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def download_quotation_pdf(self, quotation_id: str) -> bytes:
        """Download the PDF of a quotation from BoondManager.

        Args:
            quotation_id: The BoondManager quotation ID.

        Returns:
            PDF content as bytes.

        Raises:
            BoondManagerAPIError: If the download fails.
        """
        async with self._get_client() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/apps/quotations/quotations/{quotation_id}/download",
                    auth=self._auth,
                )

                if response.status_code == 404:
                    raise BoondManagerAPIError(
                        status_code=404,
                        message=f"Quotation {quotation_id} not found",
                    )

                if response.status_code >= 400:
                    raise BoondManagerAPIError(
                        status_code=response.status_code,
                        message=f"Error downloading quotation PDF: {response.text[:200]}",
                    )

                logger.info(f"Downloaded PDF for quotation {quotation_id}")
                return response.content

            except httpx.RequestError as e:
                logger.error(f"Network error downloading quotation PDF: {e}")
                raise BoondManagerAPIError(
                    status_code=0,
                    message=f"Network error: {str(e)}",
                ) from e
