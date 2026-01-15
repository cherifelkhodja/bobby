"""ERP port interface for quotation creation in BoondManager."""

from abc import ABC, abstractmethod
from typing import Protocol

from app.quotation_generator.domain.entities import Quotation


class ERPPort(ABC):
    """Interface for ERP system operations (BoondManager).

    This port defines the contract for creating quotations
    in the ERP system.
    """

    @abstractmethod
    async def create_quotation(self, quotation: Quotation) -> tuple[str, str]:
        """Create a quotation in the ERP system.

        Args:
            quotation: The quotation entity to create.

        Returns:
            Tuple of (quotation_id, reference) from the ERP.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...

    @abstractmethod
    async def validate_opportunity(self, opportunity_id: str) -> bool:
        """Validate that an opportunity exists in the ERP.

        Args:
            opportunity_id: The opportunity ID to validate.

        Returns:
            True if the opportunity exists and is valid.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...

    @abstractmethod
    async def validate_resource(self, resource_id: str) -> bool:
        """Validate that a resource exists in the ERP.

        Args:
            resource_id: The resource ID to validate.

        Returns:
            True if the resource exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...

    @abstractmethod
    async def validate_company(self, company_id: str) -> bool:
        """Validate that a company exists in the ERP.

        Args:
            company_id: The company ID to validate.

        Returns:
            True if the company exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...

    @abstractmethod
    async def validate_contact(self, contact_id: str) -> bool:
        """Validate that a contact exists in the ERP.

        Args:
            contact_id: The contact ID to validate.

        Returns:
            True if the contact exists.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...

    @abstractmethod
    async def get_next_quotation_number(self, prefix: str) -> str:
        """Get the next available quotation number.

        Args:
            prefix: Prefix for the quotation number (e.g., resource trigramme).

        Returns:
            Next available quotation number.

        Raises:
            BoondManagerAPIError: If the API call fails.
        """
        ...
