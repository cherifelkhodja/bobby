"""BoondManager CRM adapter for contract management operations."""

from typing import Any

import structlog

logger = structlog.get_logger()


class BoondCrmAdapter:
    """Adapter extending BoondClient for contract management CRM operations.

    Provides methods to fetch positionings, needs, candidates,
    and create providers and purchase orders.
    """

    def __init__(self, boond_client) -> None:
        self._boond = boond_client

    async def get_positioning(self, positioning_id: int) -> dict[str, Any] | None:
        """Fetch a positioning from BoondManager.

        Args:
            positioning_id: Boond positioning ID.

        Returns:
            Positioning data or None.
        """
        try:
            response = await self._boond._make_request(
                "GET", f"/positioning/{positioning_id}"
            )
            data = response.get("data", {})
            attributes = data.get("attributes", {})
            relationships = data.get("relationships", {})

            return {
                "id": int(data.get("id", positioning_id)),
                "state": attributes.get("state"),
                "candidate_id": self._extract_relationship_id(relationships, "resource"),
                "need_id": self._extract_relationship_id(relationships, "delivery"),
                "daily_rate": attributes.get("averageDailyPriceExcludingTax"),
                "start_date": attributes.get("startDate"),
            }
        except Exception as exc:
            logger.error(
                "boond_get_positioning_failed",
                positioning_id=positioning_id,
                error=str(exc),
            )
            return None

    async def get_need(self, need_id: int) -> dict[str, Any] | None:
        """Fetch a need/opportunity from BoondManager.

        Args:
            need_id: Boond need ID.

        Returns:
            Need data or None.
        """
        try:
            response = await self._boond._make_request(
                "GET", f"/opportunities/{need_id}"
            )
            data = response.get("data", {})
            attributes = data.get("attributes", {})
            relationships = data.get("relationships", {})

            return {
                "id": int(data.get("id", need_id)),
                "title": attributes.get("title", ""),
                "client_id": self._extract_relationship_id(relationships, "company"),
                "description": attributes.get("description", ""),
            }
        except Exception as exc:
            logger.error("boond_get_need_failed", need_id=need_id, error=str(exc))
            return None

    async def get_candidate_info(self, candidate_id: int) -> dict[str, Any] | None:
        """Fetch candidate info from BoondManager.

        Args:
            candidate_id: Boond candidate/resource ID.

        Returns:
            Candidate data or None.
        """
        try:
            response = await self._boond._make_request(
                "GET", f"/resources/{candidate_id}"
            )
            data = response.get("data", {})
            attributes = data.get("attributes", {})

            return {
                "id": int(data.get("id", candidate_id)),
                "first_name": attributes.get("firstName", ""),
                "last_name": attributes.get("lastName", ""),
                "email": attributes.get("email1", ""),
            }
        except Exception as exc:
            logger.error(
                "boond_get_candidate_failed",
                candidate_id=candidate_id,
                error=str(exc),
            )
            return None

    async def create_provider(
        self,
        company_name: str,
        siren: str,
        contact_email: str,
    ) -> int:
        """Create a provider in BoondManager.

        Args:
            company_name: Provider company name.
            siren: SIREN number.
            contact_email: Contact email.

        Returns:
            Boond provider ID.
        """
        payload = {
            "data": {
                "type": "company",
                "attributes": {
                    "name": company_name,
                    "registrationNumber": siren,
                    "email1": contact_email,
                    "typeOf": "provider",
                },
            }
        }

        response = await self._boond._make_request("POST", "/companies", json=payload)
        provider_id = int(response.get("data", {}).get("id", 0))
        logger.info(
            "boond_provider_created",
            provider_id=provider_id,
            company_name=company_name,
        )
        return provider_id

    async def create_purchase_order(
        self,
        provider_id: int,
        positioning_id: int,
        reference: str,
        amount: float,
    ) -> int:
        """Create a purchase order in BoondManager.

        Args:
            provider_id: Boond provider ID.
            positioning_id: Boond positioning ID.
            reference: Contract reference.
            amount: Order amount.

        Returns:
            Boond purchase order ID.
        """
        payload = {
            "data": {
                "type": "purchaseorder",
                "attributes": {
                    "reference": reference,
                    "amountExcludingTax": amount,
                },
                "relationships": {
                    "company": {"data": {"type": "company", "id": str(provider_id)}},
                    "positioning": {"data": {"type": "positioning", "id": str(positioning_id)}},
                },
            }
        }

        response = await self._boond._make_request("POST", "/purchase-orders", json=payload)
        po_id = int(response.get("data", {}).get("id", 0))
        logger.info(
            "boond_purchase_order_created",
            purchase_order_id=po_id,
            reference=reference,
        )
        return po_id

    @staticmethod
    def _extract_relationship_id(relationships: dict, key: str) -> int | None:
        """Extract a related entity ID from Boond relationships."""
        rel = relationships.get(key, {}).get("data", {})
        if rel and rel.get("id"):
            try:
                return int(rel["id"])
            except (ValueError, TypeError):
                return None
        return None
