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
                "GET", f"/positionings/{positioning_id}"
            )
            data = response.get("data", {})
            attributes = data.get("attributes", {})
            relationships = data.get("relationships", {})

            # Boond positioning relationships:
            # - opportunity: the need/delivery (confirmed key)
            # - dependsOn: might be the candidate/resource
            # - project, files, createdBy: other relationships
            candidate_id = (
                self._extract_relationship_id(relationships, "dependsOn")
                or self._extract_relationship_id(relationships, "resource")
                or self._extract_relationship_id(relationships, "candidate")
            )
            need_id = (
                self._extract_relationship_id(relationships, "opportunity")
                or self._extract_relationship_id(relationships, "delivery")
            )

            logger.info(
                "boond_positioning_parsed",
                positioning_id=positioning_id,
                candidate_id=candidate_id,
                need_id=need_id,
                relationship_keys=list(relationships.keys()),
            )

            return {
                "id": positioning_id,
                "state": attributes.get("state"),
                "candidate_id": candidate_id,
                "need_id": need_id,
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

        Extracts the commercial email from the mainManager relationship.

        Args:
            need_id: Boond need ID.

        Returns:
            Need data with commercial_email and commercial_name, or None.
        """
        try:
            response = await self._boond._make_request(
                "GET", f"/opportunities/{need_id}"
            )
            data = response.get("data", {})
            attributes = data.get("attributes", {})
            relationships = data.get("relationships", {})

            # Extract commercial email from mainManager via included data
            commercial_email = ""
            commercial_name = ""
            manager_id = self._extract_relationship_id(relationships, "mainManager")

            # Check included data for manager info (compare as strings)
            manager_id_str = str(manager_id) if manager_id else ""
            for included in response.get("included", []):
                if (
                    included.get("type") == "resource"
                    and str(included.get("id", "")) == manager_id_str
                ):
                    inc_attrs = included.get("attributes", {})
                    commercial_email = inc_attrs.get("email1", "") or inc_attrs.get("email2", "")
                    first_name = inc_attrs.get("firstName", "")
                    last_name = inc_attrs.get("lastName", "")
                    commercial_name = f"{first_name} {last_name}".strip()
                    break

            # If not in included, fetch the manager resource directly
            if not commercial_email and manager_id:
                try:
                    mgr_response = await self._boond._make_request(
                        "GET", f"/resources/{manager_id}"
                    )
                    mgr_data = mgr_response.get("data", {})
                    mgr_attrs = mgr_data.get("attributes", {})
                    commercial_email = mgr_attrs.get("email1", "") or mgr_attrs.get("email2", "")
                    first_name = mgr_attrs.get("firstName", "")
                    last_name = mgr_attrs.get("lastName", "")
                    commercial_name = f"{first_name} {last_name}".strip()
                except Exception as exc:
                    logger.warning(
                        "boond_get_manager_failed",
                        manager_id=manager_id,
                        error=str(exc),
                    )

            # Extract client name from included company (compare as strings)
            client_name = ""
            company_id = self._extract_relationship_id(relationships, "company")
            company_id_str = str(company_id) if company_id else ""
            for included in response.get("included", []):
                if (
                    included.get("type") == "company"
                    and str(included.get("id", "")) == company_id_str
                ):
                    client_name = included.get("attributes", {}).get("name", "")
                    break

            return {
                "id": need_id,
                "title": attributes.get("title", ""),
                "client_id": company_id,
                "client_name": client_name,
                "description": attributes.get("description", ""),
                "commercial_email": commercial_email,
                "commercial_name": commercial_name,
                "manager_id": manager_id,
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
                "id": candidate_id,
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
        result_id = response.get("data", {}).get("id")
        logger.info(
            "boond_provider_created",
            provider_id=result_id,
            company_name=company_name,
        )
        return int(result_id) if result_id else 0

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
        result_id = response.get("data", {}).get("id")
        logger.info(
            "boond_purchase_order_created",
            purchase_order_id=result_id,
            reference=reference,
        )
        return int(result_id) if result_id else 0

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
