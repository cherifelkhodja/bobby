"""BoondManager CRM adapter for contract management operations."""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class BoondCrmError(RuntimeError):
    """Erreur d'une opération CRM BoondManager (réponse 2xx sans identifiant…)."""


class BoondCrmAdapter:
    """Adapter extending BoondClient for contract management CRM operations.

    Provides methods to fetch positionings, needs, candidates,
    and create providers and purchase orders.
    """

    def __init__(self, boond_client) -> None:
        self._boond = boond_client

    @staticmethod
    def _require_created_id(response: dict[str, Any], entity: str) -> int:
        """Extrait ``data.id`` d'une réponse de création Boond.

        Lève ``BoondCrmError`` si Boond répond en 2xx sans identifiant, au lieu
        de retourner 0 (qui serait ensuite persisté comme un faux ID Boond).
        """
        result_id = response.get("data", {}).get("id")
        if not result_id:
            raise BoondCrmError(
                f"BoondManager a répondu sans identifiant lors de la création : {entity}."
            )
        return int(result_id)

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
            delivery_id = self._extract_relationship_id(relationships, "delivery")
            # Le besoin reste la référence ; sur certains positionnements Boond
            # ne renvoie que la prestation, d'où le repli historique.
            need_id = self._extract_relationship_id(relationships, "opportunity") or delivery_id

            # Detect consultant type and extract name from included data.
            # Boond can include the consultant as type "resource" (already a
            # resource in the system) or type "candidate" (still in pipeline).
            consultant_first_name = ""
            consultant_last_name = ""
            consultant_type: str | None = None
            candidate_id_str = str(candidate_id) if candidate_id else ""
            for included in response.get("included", []):
                inc_type = included.get("type", "")
                if (
                    inc_type in ("resource", "candidate")
                    and str(included.get("id", "")) == candidate_id_str
                ):
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
                delivery_id=delivery_id,
                consultant_name=f"{consultant_first_name} {consultant_last_name}".strip(),
                relationship_keys=list(relationships.keys()),
            )

            return {
                "id": positioning_id,
                "state": attributes.get("state"),
                "candidate_id": candidate_id,
                "consultant_type": consultant_type,
                "need_id": need_id,
                # Prestation Boond : support du renouvellement natif
                # (POST /deliveries/{id}/renew).
                "delivery_id": delivery_id,
                # Deux taux distincts, comme sur le bon de commande : le coût
                # journalier moyen préremplit le CJM d'achat, le tarif de vente
                # journalier le TJM — interne, jamais imprimé.
                "daily_rate": attributes.get("averageDailyCost"),
                "sale_daily_rate": attributes.get("averageDailyPriceExcludingTax"),
                "quantity": attributes.get("numberOfDaysInvoicedOrQuantity"),
                "free_days": attributes.get("numberOfDaysFree"),
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

    async def get_delivery(self, delivery_id: int) -> dict[str, Any] | None:
        """Fetch a delivery (prestation) from BoondManager.

        La prestation est l'équivalent natif du bon de commande côté Boond :
        elle porte la période, le prix de vente, le coût, les jours vendus et
        les jours de gratuité, tous renégociés à la signature. C'est donc la
        meilleure source de préremplissage d'un BDC, meilleure que le
        positionnement, qui porte les mêmes conditions mais telles qu'elles
        étaient à la proposition, et qui ignore le contrat déjà rattaché.

        Returns:
            Les données de la prestation, ou None si elle est illisible.
        """
        try:
            response = await self._boond._make_request("GET", f"/deliveries/{delivery_id}")
            return self._parse_delivery(response)
        except Exception as exc:
            logger.error("boond_get_delivery_failed", delivery_id=delivery_id, error=str(exc))
            return None

    async def renew_delivery(self, delivery_id: int) -> dict[str, Any] | None:
        """Renouvelle une prestation dans BoondManager.

        Action REST sans corps de requête : Boond duplique la prestation (mêmes
        projet, ressource et contrat) et crée, selon la configuration du
        dossier, l'achat fournisseur et la commande client associés.

        La prestation créée reprend la période de l'originale : c'est à
        l'appelant de la recaler sur les dates du nouveau bon de commande.

        Args:
            delivery_id: Prestation à renouveler.

        Returns:
            La prestation créée, ou None si l'appel échoue.
        """
        response = await self._boond._make_request("POST", f"/deliveries/{delivery_id}/renew")
        renewed = self._parse_delivery(response)
        logger.info(
            "boond_delivery_renewed",
            source_delivery_id=delivery_id,
            new_delivery_id=renewed.get("id") if renewed else None,
            purchase_id=renewed.get("purchase_id") if renewed else None,
        )
        return renewed

    async def update_delivery(  # noqa: PLR0913
        self,
        delivery_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        days_sold: float | None = None,
        free_days: float | None = None,
        purchase_daily_rate: float | None = None,
        sale_daily_rate: float | None = None,
    ) -> None:
        """Recale une prestation sur la période et les conditions d'un BDC.

        Sert après un renouvellement, la prestation créée héritant des dates de
        l'originale. Seuls les champs fournis sont envoyés.
        """
        attributes: dict[str, Any] = {}
        if start_date:
            attributes["startDate"] = start_date
        if end_date:
            attributes["endDate"] = end_date
        if days_sold is not None:
            attributes["numberOfDaysInvoicedOrQuantity"] = days_sold
        if free_days is not None:
            attributes["numberOfDaysFree"] = free_days
        if purchase_daily_rate is not None:
            attributes["averageDailyContractCost"] = purchase_daily_rate
        if sale_daily_rate is not None:
            # Le prix de vente est imposé, sinon Boond le recalcule depuis la
            # grille du projet et écraserait la valeur du bon de commande.
            attributes["averageDailyPriceExcludingTax"] = sale_daily_rate
            attributes["forceAverageDailyPriceExcludingTax"] = True

        if not attributes:
            return

        payload = {"data": {"id": str(delivery_id), "type": "delivery", "attributes": attributes}}
        await self._boond._make_request("PUT", f"/deliveries/{delivery_id}", json=payload)
        logger.info(
            "boond_delivery_updated",
            delivery_id=delivery_id,
            fields=sorted(attributes),
        )

    def _parse_delivery(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """Traduit une réponse « prestation » de Boond en données exploitables."""
        data = response.get("data") or {}
        if not data:
            return None
        attributes = data.get("attributes", {})
        relationships = data.get("relationships", {})
        included = response.get("included", [])

        # Le projet de la prestation porte le client final, le besoin et le
        # commercial. Les trois sont dans `included` : les lire ici évite trois
        # appels et reste juste même quand le besoin n'est plus lisible.
        project_id = self._extract_relationship_id(relationships, "project")
        project = self._find_included(included, "project", project_id)
        project_rels = project.get("relationships", {}) if project else {}
        client_id = self._extract_relationship_id(project_rels, "company")
        client = self._find_included(included, "company", client_id)

        try:
            parsed_id = int(data.get("id"))
        except (TypeError, ValueError):
            parsed_id = None

        return {
            "id": parsed_id,
            "state": attributes.get("state"),
            "title": attributes.get("title") or "",
            "start_date": attributes.get("startDate") or None,
            "end_date": attributes.get("endDate") or None,
            # Prix de vente au client et coût d'achat : deux notions distinctes,
            # comme le TJM et le CJM d'un bon de commande.
            "sale_daily_rate": attributes.get("averageDailyPriceExcludingTax"),
            "purchase_daily_rate": (
                attributes.get("averageDailyContractCost") or attributes.get("averageDailyCost")
            ),
            "days_sold": attributes.get("numberOfDaysInvoicedOrQuantity"),
            "free_days": attributes.get("numberOfDaysFree"),
            "resource_id": self._extract_relationship_id(relationships, "dependsOn"),
            "project_id": project_id,
            "client_id": client_id,
            "client_name": (client.get("attributes", {}).get("name") if client else None),
            "need_id": self._extract_relationship_id(project_rels, "opportunity"),
            "main_manager_id": self._extract_relationship_id(project_rels, "mainManager"),
            # Contrat déjà rattaché à la prestation : sa présence évite d'en
            # créer un second sur la même ressource.
            "contract_id": self._extract_relationship_id(relationships, "contract"),
            "purchase_id": self._extract_relationship_id(relationships, "purchase"),
        }

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
                # Extract manager ID from dependsOn relationship
                relationships = data.get("relationships", {})
                depends_on = relationships.get("dependsOn", {}).get("data", {})
                mgr_id = None
                if depends_on and depends_on.get("id"):
                    try:
                        mgr_id = int(depends_on["id"])
                    except (ValueError, TypeError):
                        pass

                return {
                    "id": candidate_id,
                    "civility": civility,
                    "first_name": attributes.get("firstName", ""),
                    "last_name": attributes.get("lastName", ""),
                    "email": attributes.get("email1", "") or attributes.get("email2", ""),
                    "phone": phone,
                    "state": attributes.get("state"),
                    "manager_id": mgr_id,
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
        provider_id = self._require_created_id(response, "société fournisseur")
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
            amount: Montant d'achat HT total de la mission.

        Returns:
            Boond purchase order ID.
        """
        # L'objet Boond est un **achat** (`purchase`), pas un « purchase order » :
        # `/purchase-orders` n'existe pas et répondait 404. C'est le même objet
        # que celui produit par le renouvellement natif d'une prestation, qui le
        # renvoie dans `relationships.purchase` — les deux chemins créent donc
        # bien la même chose.
        payload = {
            "data": {
                "type": "purchase",
                "attributes": {
                    "reference": reference,
                    # Montant d'achat total de la mission, soit
                    # (jours vendus - jours de gratuité) x CJM. L'achat Boond
                    # matérialise un engagement sur une période : c'est bien un
                    # total, pas un prix unitaire.
                    "amountExcludingTax": amount,
                },
                "relationships": {
                    "company": {"data": {"type": "company", "id": str(provider_id)}},
                    "positioning": {"data": {"type": "positioning", "id": str(positioning_id)}},
                },
            }
        }

        response = await self._boond._make_request("POST", "/purchases", json=payload)
        purchase_order_id = self._require_created_id(response, "bon de commande")
        logger.info(
            "boond_purchase_order_created",
            purchase_order_id=purchase_order_id,
            reference=reference,
        )
        return purchase_order_id

    async def resolve_resource_id(self, candidate_id: int) -> int | None:
        """Resolve the Boond resource ID from a candidate ID.

        Fetches /candidates/{id}/information and returns
        relationships.resource.data.id if present.
        """
        try:
            response = await self._boond._make_request(
                "GET", f"/candidates/{candidate_id}/information"
            )
            resource_data = (
                response.get("data", {}).get("relationships", {}).get("resource", {}).get("data")
            )
            if resource_data and resource_data.get("id"):
                return int(resource_data["id"])
        except Exception:
            pass
        return None

    async def convert_candidate_to_resource(
        self,
        candidate_id: int,
        state: int = 3,
        state_reason_type_of: int | None = None,
        type_of: int | None = None,
        manager_id: int | None = None,
    ) -> int:
        """Convert a candidate to a resource in BoondManager by updating state.

        Args:
            candidate_id: Boond candidate/resource ID.
            state: Target state (3 = Arrivée prochaine).
            state_reason_type_of: Reason type (0 = salarié, 1 = externe/sous-traitant).
            type_of: Resource type (0 = salarié, 1 = externe).
            manager_id: Boond resource ID of the manager (required by Boond as dependsOn).

        Returns:
            The new Boond resource ID (may differ from candidate_id after conversion).
        """
        attributes: dict[str, Any] = {"state": state}
        if state_reason_type_of is not None:
            attributes["stateReason"] = {"typeOf": state_reason_type_of}
        if type_of is not None:
            attributes["typeOf"] = type_of

        data_payload: dict[str, Any] = {
            "type": "resource",
            "id": str(candidate_id),
            "attributes": attributes,
        }

        if manager_id is not None:
            data_payload["relationships"] = {
                "dependsOn": {"data": {"type": "resource", "id": str(manager_id)}}
            }

        payload = {"data": data_payload}
        try:
            response = await self._boond._make_request(
                "PUT", f"/candidates/{candidate_id}/information", json=payload
            )
            # After conversion, the new resource ID is in
            # data.relationships.resource.data.id (NOT data.id which
            # remains the candidate ID).
            resource_rel = (
                response.get("data", {}).get("relationships", {}).get("resource", {}).get("data")
            )
            if resource_rel and resource_rel.get("id"):
                new_resource_id = int(resource_rel["id"])
            else:
                # Fallback: use data.id (shouldn't happen for state=3)
                new_resource_id = int(response.get("data", {}).get("id", candidate_id))
            logger.info(
                "boond_candidate_converted_to_resource",
                candidate_id=candidate_id,
                new_resource_id=new_resource_id,
                state=state,
                state_reason_type_of=state_reason_type_of,
            )
            return new_resource_id
        except Exception as exc:
            logger.error(
                "boond_convert_candidate_failed",
                candidate_id=candidate_id,
                error=str(exc),
            )
            raise

    async def _entity_exists(self, path: str, kind: str, entity_id: int) -> bool:
        """Une fiche Boond existe-t-elle ? Seul un vrai 404 vaut « non ».

        Toute autre erreur est propagée : conclure à l'absence sur un timeout
        ferait convertir un candidat qui n'en est pas un, ou recréer un
        doublon.
        """
        try:
            await self._boond._make_request("GET", path)
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("boond_entity_not_found", kind=kind, entity_id=entity_id)
                return False
            raise

    async def candidate_exists(self, candidate_id: int) -> bool:
        """Cet identifiant est-il celui d'un candidat Boond ?"""
        return await self._entity_exists(
            f"/candidates/{candidate_id}", "candidate", candidate_id
        )

    async def resource_exists(self, resource_id: int) -> bool:
        """Cet identifiant est-il celui d'une ressource Boond ?

        Les identifiants de candidats et de ressources vivent dans deux séries
        distinctes : le même numéro peut désigner deux personnes. À n'appeler
        qu'une fois établi que le numéro n'est pas celui d'un candidat.
        """
        return await self._entity_exists(f"/resources/{resource_id}", "resource", resource_id)

    async def verify_company_exists(self, company_id: int) -> bool:
        """Check if a company exists in BoondManager.

        Args:
            company_id: Boond company ID.

        Returns:
            True si la société existe, False uniquement sur un vrai 404.

        Raises:
            httpx.HTTPStatusError / autre: sur toute autre erreur (timeout, 5xx,
                réseau). On PROPAGE volontairement pour que l'appelant ne
                conclue pas à l'absence de la société et ne recrée pas un
                doublon sur une panne transitoire.
        """
        try:
            await self._boond._make_request("GET", f"/companies/{company_id}")
            return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(
                    "boond_company_not_found",
                    company_id=company_id,
                )
                return False
            raise

    async def create_company_full(  # noqa: PLR0913
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
            attributes["postcode"] = postcode
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

        logger.info(
            "boond_create_company_full_payload",
            company_name=company_name,
            agency_id=agency_id,
            has_relationships="relationships" in payload["data"],
        )

        response = await self._boond._make_request("POST", "/companies", json=payload)
        company_id = self._require_created_id(response, "société fournisseur")
        logger.info(
            "boond_company_full_created",
            company_id=company_id,
            company_name=company_name,
        )
        return company_id

    async def update_company_information(  # noqa: PLR0913
        self,
        company_id: int,
        postcode: str | None = None,
        address: str | None = None,
        town: str | None = None,
        country: str | None = None,
        legal_status: str | None = None,
        registered_office: str | None = None,
    ) -> None:
        """Update a company's information in BoondManager.

        Uses PUT /companies/{id}/information with data.attributes.postcode etc.
        """
        attributes: dict[str, Any] = {}
        if postcode:
            attributes["postcode"] = postcode
        if address:
            attributes["address"] = address
        if town:
            attributes["town"] = town
        if country:
            attributes["country"] = country
        if legal_status:
            attributes["legalStatus"] = legal_status
        if registered_office:
            attributes["registeredOffice"] = registered_office

        if not attributes:
            return

        payload: dict[str, Any] = {
            "data": {
                "attributes": attributes,
            }
        }

        logger.info(
            "boond_update_company_information",
            company_id=company_id,
            fields=list(attributes.keys()),
        )
        await self._boond._make_request("PUT", f"/companies/{company_id}/information", json=payload)
        logger.info("boond_company_information_updated", company_id=company_id)

    async def create_contact(
        self,
        company_id: int,
        civility: str | None,
        first_name: str | None,
        last_name: str | None,
        email: str | None,
        phone: str | None,
        job_title: str | None,
        types_of: list[int] | None = None,
        postcode: str | None = None,
        address: str | None = None,
        town: str | None = None,
        agency_id: int | None = None,
    ) -> int:
        """Create a contact linked to a company in BoondManager.

        Args:
            company_id: Boond company ID.
            civility: Civility string ("M." → 0 homme, "Mme" → 1 femme).
            first_name: First name.
            last_name: Last name.
            email: Email address.
            phone: Phone number.
            job_title: Job title / fonction.
            types_of: List of contact types (1=dirigeant, 2=facturation, 3=adv, etc.).
            postcode: Postal code.
            address: Street address.
            town: City.
            agency_id: Boond agency ID.

        Returns:
            Boond contact ID.
        """
        # Boond civility: 0 = homme, 1 = femme
        civility_map = {"M.": 0, "M": 0, "Mme": 1}
        civility_int = civility_map.get(civility or "", 0)

        attributes: dict[str, Any] = {
            "typesOf": types_of or [],
            "civility": civility_int,
            "state": 9,
        }
        if first_name:
            attributes["firstName"] = first_name
        if last_name:
            attributes["lastName"] = last_name
        if email:
            attributes["email1"] = email
        if phone:
            attributes["phone1"] = phone
        if job_title:
            attributes["function"] = job_title
        if postcode:
            attributes["postcode"] = postcode
        if address:
            attributes["address"] = address
        if town:
            attributes["town"] = town

        relationships: dict[str, Any] = {
            "company": {"data": {"type": "company", "id": str(company_id)}}
        }
        if agency_id:
            relationships["agency"] = {"data": {"type": "agency", "id": str(agency_id)}}

        payload = {
            "data": {
                "type": "contact",
                "attributes": attributes,
                "relationships": relationships,
            }
        }

        response = await self._boond._make_request("POST", "/contacts", json=payload)
        contact_id = self._require_created_id(response, "contact")
        logger.info(
            "boond_contact_created",
            contact_id=contact_id,
            company_id=company_id,
            types_of=types_of,
        )
        return contact_id

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
        start_date: str | None = None,
        end_date: str | None = None,
        agency_id: int | None = None,
    ) -> int:
        """Create a contract in BoondManager for an external consultant.

        Args:
            resource_id: Boond resource ID.
            positioning_id: Boond positioning ID.
            daily_rate: Average daily production cost (TJM).
            type_of: Contract type (2=sous-traitant, 3=freelance,
                     6=portage salarial, 7=portage commercial).
            start_date: Contract start date (YYYY-MM-DD format).
            end_date: Contract end date (YYYY-MM-DD format).
            agency_id: Boond agency ID to link the contract to.

        Returns:
            Boond contract ID.
        """
        attributes: dict[str, Any] = {
            "typeOf": type_of,
            "forceContractAverageDailyProductionCost": True,
            "contractAverageDailyProductionCost": daily_rate,
            "numberOfHoursPerWeek": 35,
            "numberOfWorkingDays": 210,
            "classification": "-1",
            "currency": 0,
            "workingTimeType": 0,
        }
        if start_date:
            attributes["startDate"] = start_date
        if end_date:
            attributes["endDate"] = end_date

        relationships: dict[str, Any] = {
            "dependsOn": {"data": {"type": "resource", "id": str(resource_id)}},
            "positioning": {"data": {"type": "positioning", "id": str(positioning_id)}},
        }
        if agency_id:
            relationships["agency"] = {"data": {"type": "agency", "id": str(agency_id)}}

        payload = {
            "data": {
                "type": "contract",
                "attributes": attributes,
                "relationships": relationships,
            }
        }

        logger.info(
            "boond_contract_payload",
            resource_id=resource_id,
            positioning_id=positioning_id,
            payload=payload,
        )
        response = await self._boond._make_request("POST", "/contracts", json=payload)
        contract_id = self._require_created_id(response, "contrat")
        logger.info(
            "boond_contract_created",
            contract_id=contract_id,
            resource_id=resource_id,
            positioning_id=positioning_id,
        )
        return contract_id

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
            "providerCompany": {"data": {"type": "company", "id": str(provider_company_id)}}
        }
        if provider_contact_id:
            relationships["providerContact"] = {
                "data": {"type": "contact", "id": str(provider_contact_id)}
            }

        payload = {
            "data": {
                "id": str(resource_id),
                "type": "resource",
                "attributes": {},
                "relationships": relationships,
            }
        }

        await self._boond._make_request(
            "PUT", f"/resources/{resource_id}/administrative", json=payload
        )
        logger.info(
            "boond_resource_administrative_updated",
            resource_id=resource_id,
            provider_company_id=provider_company_id,
            provider_contact_id=provider_contact_id,
        )

    async def update_company_bank_details(
        self,
        company_id: int,
        iban: str,
        bic: str,
        description: str = "RIB Fournisseur",
    ) -> None:
        """Push bank details (IBAN/BIC) to a Boond company via SEPA app.

        Uses PUT /apps/sepa/companies/{id} to create a bank detail entry.

        Args:
            company_id: Boond company ID.
            iban: IBAN (max 34 chars, no spaces).
            bic: BIC/SWIFT code (max 11 chars).
            description: Label for the bank detail.
        """
        # Remove spaces from IBAN for Boond
        clean_iban = iban.replace(" ", "")

        payload = {
            "data": {
                "id": str(company_id),
                "type": "appsepacompany",
                "attributes": {
                    "banksDetails": [
                        {
                            "description": description,
                            "iban": clean_iban,
                            "bic": bic,
                        }
                    ]
                },
            }
        }

        await self._boond._make_request("PUT", f"/apps/sepa/companies/{company_id}", json=payload)
        logger.info(
            "boond_company_bank_details_updated",
            company_id=company_id,
            iban_last4=clean_iban[-4:] if len(clean_iban) >= 4 else "****",
        )

    @staticmethod
    def _find_included(included: list, entity_type: str, entity_id: object) -> dict | None:
        """Retrouve une entité du bloc `included` par type et identifiant.

        Boond renvoie les identifiants en chaîne dans `included` et parfois en
        entier dans les relations : la comparaison se fait donc sur le texte.
        """
        if entity_id is None:
            return None
        wanted = str(entity_id)
        for entry in included:
            if entry.get("type") == entity_type and str(entry.get("id", "")) == wanted:
                return entry
        return None

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
