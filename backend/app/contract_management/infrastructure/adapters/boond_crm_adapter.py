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

        Extracts consultant info (name) from the ``included`` array
        using the ``dependsOn`` relationship, which points to the
        resource assigned to the positioning.

        Args:
            positioning_id: Boond positioning ID.

        Returns:
            Positioning data or None.
        """
        try:
            response = await self._boond._make_request("GET", f"/positionings/{positioning_id}")
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
            need_id = self._extract_relationship_id(
                relationships, "opportunity"
            ) or self._extract_relationship_id(relationships, "delivery")

            # Detect consultant type and extract name from included data.
            # Boond can include the consultant as type "resource" (already a
            # resource in the system) or type "candidate" (still in pipeline).
            consultant_first_name = ""
            consultant_last_name = ""
            consultant_type: str | None = None
            candidate_id_str = str(candidate_id) if candidate_id else ""
            for included in response.get("included", []):
                inc_type = included.get("type", "")
                if inc_type in ("resource", "candidate") and str(included.get("id", "")) == candidate_id_str:
                    consultant_type = inc_type
                    inc_attrs = included.get("attributes", {})
                    consultant_first_name = inc_attrs.get("firstName", "")
                    consultant_last_name = inc_attrs.get("lastName", "")
                    break

            # Fallback: infer type from relationship key used to find the ID
            if consultant_type is None and candidate_id is not None:
                if self._extract_relationship_id(relationships, "resource") == candidate_id:
                    consultant_type = "resource"
                elif self._extract_relationship_id(relationships, "candidate") == candidate_id:
                    consultant_type = "candidate"

            logger.info(
                "boond_positioning_parsed",
                positioning_id=positioning_id,
                candidate_id=candidate_id,
                consultant_type=consultant_type,
                need_id=need_id,
                consultant_name=f"{consultant_first_name} {consultant_last_name}".strip(),
                relationship_keys=list(relationships.keys()),
            )

            return {
                "id": positioning_id,
                "state": attributes.get("state"),
                "candidate_id": candidate_id,
                "consultant_type": consultant_type,
                "need_id": need_id,
                "daily_rate": attributes.get("averageDailyPriceExcludingTax"),
                "quantity": attributes.get("numberOfDaysInvoicedOrQuantity"),
                "start_date": attributes.get("startDate"),
                "end_date": attributes.get("endDate"),
                "consultant_first_name": consultant_first_name,
                "consultant_last_name": consultant_last_name,
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
                "GET", f"/opportunities/{need_id}/information"
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

            agency_id = self._extract_relationship_id(relationships, "agency")

            # Fallback: if /information didn't return the agency relationship,
            # fetch the base opportunity endpoint which always includes it.
            if agency_id is None:
                try:
                    base_response = await self._boond._make_request(
                        "GET", f"/opportunities/{need_id}"
                    )
                    base_rels = base_response.get("data", {}).get("relationships", {})
                    agency_id = self._extract_relationship_id(base_rels, "agency")
                except Exception as exc:
                    logger.warning(
                        "boond_get_opportunity_base_failed",
                        need_id=need_id,
                        error=str(exc),
                    )

            return {
                "id": need_id,
                "title": attributes.get("title", ""),
                "client_id": company_id,
                "client_name": client_name,
                "description": attributes.get("description", ""),
                "commercial_email": commercial_email,
                "commercial_name": commercial_name,
                "manager_id": manager_id,
                "agency_id": agency_id,
            }
        except Exception as exc:
            logger.error("boond_get_need_failed", need_id=need_id, error=str(exc))
            return None

    async def get_candidate_info(
        self,
        candidate_id: int,
        consultant_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch consultant info from BoondManager.

        Routes to /candidates/{id} for actual Boond candidates (type="candidate")
        or to /resources/{id} for already-registered resources (type="resource").
        When consultant_type is unknown (None), tries /resources/ first then
        falls back to /candidates/.

        Args:
            candidate_id: Boond candidate or resource ID.
            consultant_type: "candidate", "resource", or None (unknown).

        Returns:
            Consultant data or None.
        """
        endpoints: list[str]
        if consultant_type == "candidate":
            endpoints = [f"/candidates/{candidate_id}/information"]
        elif consultant_type == "resource":
            endpoints = [f"/resources/{candidate_id}/information"]
        else:
            # Unknown type: try resource first (most common), then candidate
            endpoints = [
                f"/resources/{candidate_id}/information",
                f"/candidates/{candidate_id}/information",
            ]

        last_exc: Exception | None = None
        for endpoint in endpoints:
            try:
                response = await self._boond._make_request("GET", endpoint)
                data = response.get("data", {})
                attributes = data.get("attributes", {})

                # civility: 0 = homme (M.), 1 = femme (Mme)
                raw_civility = attributes.get("civility")
                civility = None
                if raw_civility == 0:
                    civility = "M."
                elif raw_civility == 1:
                    civility = "Mme"

                phone = (
                    attributes.get("phone1")
                    or attributes.get("mobilePhone")
                    or attributes.get("phone2")
                    or ""
                )
                return {
                    "id": candidate_id,
                    "civility": civility,
                    "first_name": attributes.get("firstName", ""),
                    "last_name": attributes.get("lastName", ""),
                    "email": attributes.get("email1", "") or attributes.get("email2", ""),
                    "phone": phone,
                }
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "boond_get_consultant_info_endpoint_failed",
                    candidate_id=candidate_id,
                    endpoint=endpoint,
                    error=str(exc),
                )

        logger.error(
            "boond_get_candidate_failed",
            candidate_id=candidate_id,
            consultant_type=consultant_type,
            error=str(last_exc),
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

    async def convert_candidate_to_resource(
        self,
        candidate_id: int,
        state: int = 3,
    ) -> None:
        """Convert a candidate to a resource in BoondManager by updating state.

        Args:
            candidate_id: Boond candidate/resource ID.
            state: Target state (3 = Arrivée prochaine).
        """
        payload = {
            "data": {
                "type": "resource",
                "id": str(candidate_id),
                "attributes": {"state": state},
            }
        }
        try:
            await self._boond._make_request(
                "PUT", f"/candidates/{candidate_id}/information", json=payload
            )
            logger.info(
                "boond_candidate_converted_to_resource",
                candidate_id=candidate_id,
                state=state,
            )
        except Exception as exc:
            logger.error(
                "boond_convert_candidate_failed",
                candidate_id=candidate_id,
                error=str(exc),
            )
            raise

    async def create_company_full(
        self,
        company_name: str,
        state: int,
        postcode: str | None,
        address: str | None,
        town: str | None,
        country: str,
        vat_number: str | None,
        siret: str | None,
        legal_status: str | None,
        registered_office: str | None,
        ape_code: str,
        agency_id: int | None,
    ) -> int:
        """Create a provider company in BoondManager with full details.

        Args:
            company_name: Company name.
            state: Company state (9 = fournisseur actif).
            postcode: Postal code.
            address: Street address.
            town: City.
            country: Country name.
            vat_number: VAT number (numéro TVA intracommunautaire).
            siret: SIRET number (14 digits).
            legal_status: Legal status string, e.g. "SAS au capital de 1000€".
            registered_office: RCS string, e.g. "535 028 856 R.C.S. Rennes".
            ape_code: APE/NAF code, e.g. "6202A".
            agency_id: Boond agency ID to link the company to.

        Returns:
            Boond company ID.
        """
        attributes: dict[str, Any] = {
            "name": company_name,
            "state": state,
            "typeOf": "provider",
            "expertiseArea": "informatique",
            "apeCode": ape_code,
        }
        if postcode:
            attributes["postCode"] = postcode
        if address:
            attributes["address"] = address
        if town:
            attributes["town"] = town
        if country:
            attributes["country"] = country
        if vat_number:
            attributes["vatNumber"] = vat_number
        if siret:
            attributes["registrationNumber"] = siret
        if legal_status:
            attributes["legalStatus"] = legal_status
        if registered_office:
            attributes["registeredOffice"] = registered_office

        payload: dict[str, Any] = {
            "data": {
                "type": "company",
                "attributes": attributes,
            }
        }

        if agency_id:
            payload["data"]["relationships"] = {
                "agency": {"data": {"type": "agency", "id": str(agency_id)}}
            }

        response = await self._boond._make_request("POST", "/companies", json=payload)
        result_id = response.get("data", {}).get("id")
        logger.info(
            "boond_company_full_created",
            company_id=result_id,
            company_name=company_name,
        )
        return int(result_id) if result_id else 0

    async def create_contact(
        self,
        company_id: int,
        civility: str | None,
        first_name: str | None,
        last_name: str | None,
        email: str | None,
        phone: str | None,
        job_title: str | None,
        type_of: int,
    ) -> int:
        """Create a contact linked to a company in BoondManager.

        Args:
            company_id: Boond company ID.
            civility: Civility string ("M." → 1, "Mme" → 2).
            first_name: First name.
            last_name: Last name.
            email: Email address.
            phone: Phone number.
            job_title: Job title / fonction.
            type_of: Contact type (7=dirigeant, 9=adv, 2=facturation).

        Returns:
            Boond contact ID.
        """
        civility_map = {"M.": 1, "Mme": 2, "M": 1}
        civility_int = civility_map.get(civility or "", 1)

        attributes: dict[str, Any] = {"typeOf": type_of, "civility": civility_int}
        if first_name:
            attributes["firstName"] = first_name
        if last_name:
            attributes["lastName"] = last_name
        if email:
            attributes["email1"] = email
        if phone:
            attributes["phone1"] = phone
        if job_title:
            attributes["jobTitle"] = job_title

        payload = {
            "data": {
                "type": "contact",
                "attributes": attributes,
                "relationships": {
                    "company": {"data": {"type": "company", "id": str(company_id)}}
                },
            }
        }

        response = await self._boond._make_request("POST", "/contacts", json=payload)
        result_id = response.get("data", {}).get("id")
        logger.info(
            "boond_contact_created",
            contact_id=result_id,
            company_id=company_id,
            type_of=type_of,
        )
        return int(result_id) if result_id else 0

    async def get_resource_type_of(self, resource_id: int) -> int | None:
        """Fetch the typeOf attribute of a resource.

        Args:
            resource_id: Boond resource ID.

        Returns:
            typeOf integer (0=salarié, 1=externe) or None on error.
        """
        try:
            response = await self._boond._make_request("GET", f"/resources/{resource_id}")
            type_of = response.get("data", {}).get("attributes", {}).get("typeOf")
            return int(type_of) if type_of is not None else None
        except Exception as exc:
            logger.error(
                "boond_get_resource_type_of_failed",
                resource_id=resource_id,
                error=str(exc),
            )
            return None

    async def create_boond_contract(
        self,
        resource_id: int,
        positioning_id: int,
        daily_rate: float,
        type_of: int,
    ) -> int:
        """Create a contract in BoondManager for an external consultant.

        Args:
            resource_id: Boond resource ID.
            positioning_id: Boond positioning ID.
            daily_rate: Average daily production cost (TJM).
            type_of: Contract type (2=sous-traitant, 3=freelance,
                     6=portage salarial, 7=portage commercial).

        Returns:
            Boond contract ID.
        """
        payload = {
            "data": {
                "type": "contract",
                "attributes": {
                    "typeOf": type_of,
                    "contractAverageDailyProductionCost": daily_rate,
                    "numberOfHoursPerWeek": 35,
                },
                "relationships": {
                    "resource": {"data": {"type": "resource", "id": str(resource_id)}},
                    "positioning": {
                        "data": {"type": "positioning", "id": str(positioning_id)}
                    },
                },
            }
        }

        response = await self._boond._make_request("POST", "/contracts", json=payload)
        result_id = response.get("data", {}).get("id")
        logger.info(
            "boond_contract_created",
            contract_id=result_id,
            resource_id=resource_id,
            positioning_id=positioning_id,
        )
        return int(result_id) if result_id else 0

    async def update_resource_administrative(
        self,
        resource_id: int,
        provider_company_id: int,
        provider_contact_id: int | None,
    ) -> None:
        """Link a resource to its provider company and contact (administrative data).

        Args:
            resource_id: Boond resource ID.
            provider_company_id: Boond company ID of the provider.
            provider_contact_id: Boond contact ID of the main provider contact.
        """
        relationships: dict[str, Any] = {
            "providerCompany": {
                "data": {"type": "company", "id": str(provider_company_id)}
            }
        }
        if provider_contact_id:
            relationships["providerContact"] = {
                "data": {"type": "contact", "id": str(provider_contact_id)}
            }

        payload = {"data": {"relationships": relationships}}

        await self._boond._make_request(
            "PUT", f"/resources/{resource_id}/administrative", json=payload
        )
        logger.info(
            "boond_resource_administrative_updated",
            resource_id=resource_id,
            provider_company_id=provider_company_id,
            provider_contact_id=provider_contact_id,
        )

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
