"""Tests for BoondCrmAdapter CRM operations.

Verrouille deux correctifs :

1. ``verify_company_exists`` ne conclut à l'absence de la société (``False``)
   QUE sur un vrai 404. Sur 5xx, timeout ou erreur réseau, l'exception est
   PROPAGÉE pour ne pas recréer un doublon sur une panne transitoire.
2. Les méthodes ``create_*`` lèvent ``BoondCrmError`` (via ``_require_created_id``)
   quand BoondManager répond en 2xx sans ``data.id``, au lieu de persister un
   faux identifiant (0 / None).

``_make_request`` renvoie le ``response.json()`` de Boond, donc un ``dict`` :
les mocks retournent des dicts et les erreurs sont simulées via ``side_effect``.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.contract_management.infrastructure.adapters.boond_crm_adapter import (
    BoondCrmAdapter,
    BoondCrmError,
)


def _make_adapter() -> tuple[BoondCrmAdapter, AsyncMock]:
    """Build the adapter with a mocked Boond client.

    Le constructeur réel est ``BoondCrmAdapter(boond_client)`` et stocke
    ``self._boond = boond_client``. On retourne aussi le client mocké pour que
    chaque test câble ``_make_request`` (AsyncMock) à sa guise.
    """
    boond_client = AsyncMock()
    boond_client._make_request = AsyncMock()
    adapter = BoondCrmAdapter(boond_client)
    return adapter, boond_client


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build a real ``httpx.HTTPStatusError`` exposing ``response.status_code``.

    L'adapter inspecte ``exc.response.status_code`` : on construit donc une
    vraie ``httpx.Response`` porteuse de ce code, comme ``raise_for_status`` le
    ferait en production.
    """
    request = httpx.Request("GET", "https://boond.test/companies/1")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


class TestPositioning:
    """La lecture d'un positionnement, et l'écriture de son état.

    **Un seul appel suffit** : le bloc `included` porte le besoin avec son
    commercial, son client et son agence, le projet, et le consultant avec la
    ressource qui lui correspond déjà.

    Le `PUT` rend le positionnement à jour dans la même forme : le relire
    ensuite n'apprendrait rien de plus.
    """

    @staticmethod
    def _response(*, state=2, resource=None, project="224") -> dict:
        """Réponse réelle du CRM pour le positionnement 539."""
        candidate = {
            "id": "2398",
            "type": "candidate",
            "attributes": {"lastName": "CHEBBI", "firstName": "Rym", "typeOf": 10},
            "relationships": {"agency": {"data": {"id": "5", "type": "agency"}}},
        }
        if resource:
            candidate["relationships"]["resource"] = {"data": {"id": resource, "type": "resource"}}
        return {
            "data": {
                "id": "539",
                "type": "positioning",
                "attributes": {
                    "state": state,
                    "startDate": "2026-07-06",
                    "endDate": "2026-12-31",
                    "averageDailyPriceExcludingTax": 620,
                    "averageDailyCost": 585,
                    "numberOfDaysInvoicedOrQuantity": 126,
                    "numberOfDaysFree": 2,
                },
                "relationships": {
                    "opportunity": {"data": {"id": "1628", "type": "opportunity"}},
                    "project": {"data": {"id": project, "type": "project"}} if project else {},
                    "files": {"data": []},
                    "dependsOn": {"data": {"id": "2398", "type": "candidate"}},
                    "createdBy": {"data": {"id": "1", "type": "resource"}},
                },
            },
            "included": [
                {"id": "1", "type": "resource", "attributes": {"lastName": "EL KHODJA"}},
                {"id": "262", "type": "company", "attributes": {"name": "BNP Paribas AM"}},
                {
                    "id": "1628",
                    "type": "opportunity",
                    "attributes": {"title": "Developpement JAVA", "reference": "AO1628"},
                    "relationships": {
                        "mainManager": {"data": {"id": "1", "type": "resource"}},
                        "company": {"data": {"id": "262", "type": "company"}},
                    },
                },
                {"id": "224", "type": "project", "attributes": {"reference": "AMFR"}},
                {"id": "5", "type": "agency", "attributes": {}},
                candidate,
            ],
        }

    @pytest.mark.asyncio
    async def test_one_call_gives_the_whole_context(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response())

        positioning = await adapter.get_positioning(539)

        assert boond._make_request.await_count == 1
        assert positioning["need_id"] == 1628
        assert positioning["need_title"] == "Developpement JAVA"
        assert positioning["client_name"] == "BNP Paribas AM"
        assert positioning["manager_id"] == 1
        assert positioning["agency_id"] == 5
        assert positioning["project_id"] == 224

    @pytest.mark.asyncio
    async def test_the_consultant_says_his_own_nature(self):
        """`dependsOn.type` tranche candidat ou ressource : rien à sonder."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response())

        positioning = await adapter.get_positioning(539)

        assert positioning["candidate_id"] == 2398
        assert positioning["consultant_type"] == "candidate"
        assert positioning["consultant_last_name"] == "CHEBBI"
        assert positioning["resource_id"] is None

    @pytest.mark.asyncio
    async def test_a_candidate_already_converted_carries_his_resource(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response(resource="2870"))

        assert (await adapter.get_positioning(539))["resource_id"] == 2870

    @pytest.mark.asyncio
    async def test_the_conditions_of_the_mission_are_read(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response())

        positioning = await adapter.get_positioning(539)

        assert positioning["daily_rate"] == 585
        assert positioning["sale_daily_rate"] == 620
        assert positioning["quantity"] == 126
        assert positioning["free_days"] == 2

    @pytest.mark.asyncio
    async def test_writing_the_state_sends_only_the_state(self):
        """Dates, tarif et jours restent ceux du commercial."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response())

        await adapter.update_positioning_state(539, 2)

        call = boond._make_request.await_args
        assert call.args[:2] == ("PUT", "/positionings/539")
        assert call.kwargs["json"]["data"]["attributes"] == {"state": 2}

    @pytest.mark.asyncio
    async def test_the_write_returns_the_updated_positioning(self):
        """Sa réponse porte l'état pris et le projet : la relire n'apprend rien."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response())

        positioning = await adapter.update_positioning_state(539, 2)

        assert boond._make_request.await_count == 1
        assert positioning["state"] == 2
        assert positioning["project_id"] == 224

    @pytest.mark.asyncio
    async def test_a_state_boond_did_not_take_is_visible(self):
        """Une réponse en 200 ne prouve pas que le changement a été pris."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._response(state=7))

        assert (await adapter.update_positioning_state(539, 2))["state"] == 7

    @pytest.mark.asyncio
    async def test_an_unreadable_positioning_gives_nothing(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=RuntimeError("Boond 500"))

        assert await adapter.get_positioning(539) is None


class TestCandidateConversion:
    """La conversion d'un candidat en ressource, et le numéro qu'elle rend.

    `data.id` reste **celui du candidat** après la conversion : la ressource
    née de l'opération est dans `data.relationships.resource`. Retomber sur
    `data.id` rendait un numéro de candidat déguisé en ressource, et la suite
    du report échouait en 404 sur `/resources/{id}/administrative`.
    """

    @staticmethod
    def _converted(resource_id: str | None = "2870") -> dict:
        relationships = (
            {"resource": {"data": {"id": resource_id, "type": "resource"}}} if resource_id else {}
        )
        return {"data": {"id": "2398", "type": "resource", "relationships": relationships}}

    @pytest.mark.asyncio
    async def test_the_new_resource_is_returned(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._converted())

        assert await adapter.convert_candidate_to_resource(2398) == 2870

    @pytest.mark.asyncio
    async def test_the_candidate_id_is_never_returned_as_a_resource(self):
        """Le 404 sur `/resources/2398/administrative` venait de là."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            side_effect=[self._converted(resource_id=None), {"data": {"relationships": {}}}]
        )

        with pytest.raises(BoondCrmError):
            await adapter.convert_candidate_to_resource(2398)

    @pytest.mark.asyncio
    async def test_the_candidate_sheet_is_read_when_the_write_stays_silent(self):
        """Boond ne rend pas toujours la relation dans la réponse de l'écriture."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            side_effect=[
                self._converted(resource_id=None),
                {"data": {"relationships": {"resource": {"data": {"id": "2870"}}}}},
            ]
        )

        assert await adapter.convert_candidate_to_resource(2398) == 2870
        assert boond._make_request.await_args_list[1].args == (
            "GET",
            "/candidates/2398/information",
        )


class TestSupplierPurchase:
    """L'achat fournisseur : un corps minimal, Boond déduit le reste.

    Il se rattache à une **prestation**, pas à un positionnement, et
    **seulement à la création** : `PUT /purchases/{id}/information` n'expose ni
    `delivery` ni `project`. Un achat posé sur la mauvaise prestation se
    supprime et se recrée.
    """

    @staticmethod
    def _body(boond: AsyncMock) -> dict:
        call = boond._make_request.await_args
        assert call.args[:2] == ("POST", "/purchases")
        return call.kwargs["json"]["data"]

    @pytest.mark.asyncio
    async def test_the_purchase_hangs_on_its_project_and_delivery(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "666"}})

        purchase_id = await adapter.create_supplier_purchase(
            project_id=224, delivery_id=804, title="CHEBBI Rym - AKEMA TECH - GEM-BC-001"
        )

        assert purchase_id == 666
        data = self._body(boond)
        assert data["type"] == "purchase"
        assert data["relationships"] == {
            "project": {"data": {"type": "project", "id": "224"}},
            "delivery": {"data": {"type": "delivery", "id": "804"}},
        }

    @pytest.mark.asyncio
    async def test_nothing_is_dictated_that_boond_can_deduce(self):
        """Montants, période, société, agence : la prestation les porte déjà.

        Le montant surtout : Boond compte `quantity` x `amountExcludingTax`, ce
        dernier **unitaire**. Y poser le total du bon de commande le faisait
        multiplier une seconde fois.
        """
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "666"}})

        await adapter.create_supplier_purchase(project_id=224, delivery_id=804, title="GEM-BC-001")

        assert set(self._body(boond)["attributes"]) == {"title", "createPayments"}

    @pytest.mark.asyncio
    async def test_payments_are_not_scheduled_by_boond(self):
        """L'omettre laissait Boond échelonner l'achat de lui-même."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "666"}})

        await adapter.create_supplier_purchase(project_id=224, delivery_id=804, title="GEM-BC-001")

        assert self._body(boond)["attributes"]["createPayments"] is None

    @pytest.mark.asyncio
    async def test_a_long_title_is_cut_to_what_boond_accepts(self):
        """`TAB_ACHAT.ACHAT_TITLE` est borné : au-delà, la création est refusée."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "666"}})

        await adapter.create_supplier_purchase(project_id=224, delivery_id=804, title="X" * 400)

        assert len(self._body(boond)["attributes"]["title"]) == 150

    @pytest.mark.asyncio
    async def test_a_creation_without_id_is_an_error(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {}})

        with pytest.raises(BoondCrmError):
            await adapter.create_supplier_purchase(
                project_id=224, delivery_id=804, title="GEM-BC-001"
            )


class TestProjectDeliveryLookup:
    """Retrouver la prestation d'une mission parmi celles de son projet.

    Un positionnement n'expose **aucune** relation `delivery` — vérifié contre
    le CRM sur les positionnements 538 et 539, dont les relations sont
    `opportunity`, `project`, `files`, `dependsOn` et `createdBy`. Le lien passe
    par l'onglet des prestations du projet.

    Un projet en porte **plusieurs** : une par consultant, et une de plus à
    chaque reconduction du même. Le rattachement se fait donc sur les données de
    la mission — un achat posé sur la mauvaise prestation ne se corrige qu'en le
    supprimant et le recréant.
    """

    @staticmethod
    def _delivery(did, rid, start="2026-07-06", end="2026-12-31", days=126) -> dict:
        return {
            "id": str(did),
            "type": "delivery",
            "attributes": {
                "startDate": start,
                "endDate": end,
                "numberOfDaysInvoicedOrQuantity": days,
            },
            "relationships": {
                "dependsOn": {"data": {"id": str(rid), "type": "resource"}},
                "purchase": {"data": None},
                "project": {"data": {"id": "224", "type": "project"}},
            },
        }

    @classmethod
    def _tab(cls, *entries) -> dict:
        """Réponse type de `GET /projects/{id}/deliveries-groupments`."""
        return {"meta": {"totals": {"rows": len(entries)}}, "data": list(entries), "included": []}

    @pytest.mark.asyncio
    async def test_the_only_delivery_of_the_consultant_is_taken(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._tab(self._delivery(804, 2870)))

        assert await adapter.find_project_delivery(224, resource_id=2870) == 804

    @pytest.mark.asyncio
    async def test_the_deliveries_tab_of_the_project_is_read(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._tab(self._delivery(804, 2870)))

        await adapter.find_project_delivery(224)

        assert boond._make_request.await_args.args == (
            "GET",
            "/projects/224/deliveries-groupments",
        )

    @pytest.mark.asyncio
    async def test_the_delivery_of_another_consultant_is_never_taken(self):
        """Même seule du projet : l'achat partirait sur la mission d'un autre."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value=self._tab(self._delivery(804, 2999)))

        assert await adapter.find_project_delivery(224, resource_id=2870) is None

    @pytest.mark.asyncio
    async def test_the_consultant_singles_his_out(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(self._delivery(804, 2870), self._delivery(805, 2999))
        )

        assert await adapter.find_project_delivery(224, resource_id=2999) == 805

    @pytest.mark.asyncio
    async def test_a_renewal_is_separated_by_its_period(self):
        """Deux prestations du même consultant sur le même projet : la période tranche."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(
                self._delivery(804, 2870, start="2026-07-06", end="2026-12-31"),
                self._delivery(806, 2870, start="2027-01-01", end="2027-06-30"),
            )
        )

        found = await adapter.find_project_delivery(
            224, resource_id=2870, start_date="2027-01-01", end_date="2027-06-30"
        )

        assert found == 806

    @pytest.mark.asyncio
    async def test_the_days_separate_what_the_period_leaves_tied(self):
        """Deux prestations sur la même période, avenant ou correction."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(
                self._delivery(804, 2870, days=126),
                self._delivery(807, 2870, days=90),
            )
        )

        found = await adapter.find_project_delivery(
            224,
            resource_id=2870,
            start_date="2026-07-06",
            end_date="2026-12-31",
            days_sold=90,
        )

        assert found == 807

    @pytest.mark.asyncio
    async def test_an_ambiguous_choice_gives_nothing(self):
        """Rien ne les distingue : l'ADV rattachera à la main."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(self._delivery(804, 2870), self._delivery(808, 2870))
        )

        found = await adapter.find_project_delivery(
            224, resource_id=2870, start_date="2026-07-06", end_date="2026-12-31", days_sold=126
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_a_period_matching_none_of_them_gives_nothing(self):
        """Mieux vaut pas de prestation qu'une prestation approchante."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(
                self._delivery(804, 2870, start="2026-07-06"),
                self._delivery(806, 2870, start="2027-01-01"),
            )
        )

        found = await adapter.find_project_delivery(
            224, resource_id=2870, start_date="2028-03-01", end_date="2028-09-30"
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_groupments_are_not_mistaken_for_deliveries(self):
        """L'onglet mêle les deux ; seule une prestation peut recevoir un achat."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(
                self._delivery(804, 2870), {"id": "12", "type": "groupment", "relationships": {}}
            )
        )

        assert await adapter.find_project_delivery(224, resource_id=2870) == 804

    @pytest.mark.asyncio
    async def test_a_project_without_delivery_gives_nothing(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": [], "included": []})

        assert await adapter.find_project_delivery(224, resource_id=2870) is None

    @pytest.mark.asyncio
    async def test_a_decimal_quantity_still_matches(self):
        """Boond rend les jours tantôt entiers, tantôt décimaux."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value=self._tab(
                self._delivery(804, 2870, days=126.0), self._delivery(807, 2870, days=90.5)
            )
        )

        found = await adapter.find_project_delivery(
            224, resource_id=2870, start_date="2026-07-06", end_date="2026-12-31", days_sold=90.5
        )

        assert found == 807


class TestSuppressions:
    """Défaire un report : un 404 vaut suppression, le reste doit remonter."""

    @pytest.mark.asyncio
    async def test_chaque_objet_a_son_endpoint(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={})

        await adapter.delete_supplier_purchase(666)
        await adapter.delete_boond_contract(555)
        await adapter.delete_delivery(797)

        appels = [(c.args[0], c.args[1]) for c in boond._make_request.await_args_list]
        assert appels == [
            ("DELETE", "/purchases/666"),
            ("DELETE", "/contracts/555"),
            ("DELETE", "/deliveries/797"),
        ]

    @pytest.mark.asyncio
    async def test_un_objet_deja_absent_compte_comme_supprime(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(404))

        assert await adapter.delete_supplier_purchase(666) is True

    @pytest.mark.asyncio
    async def test_un_refus_est_propage(self):
        """Conclure à la suppression sur un 403 ferait créer un doublon ensuite."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(403))

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.delete_boond_contract(555)


class TestVerifyCompanyExists:
    """``verify_company_exists`` : False seulement sur 404, propage sinon."""

    @pytest.mark.asyncio
    async def test_returns_true_when_found(self):
        """Réponse 2xx -> la société existe (True)."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "123"}})

        result = await adapter.verify_company_exists(123)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_only_on_404(self):
        """Un vrai 404 -> société absente (False)."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(404))

        result = await adapter.verify_company_exists(123)

        assert result is False

    @pytest.mark.asyncio
    async def test_propagates_on_500(self):
        """Une HTTPStatusError 5xx est PROPAGÉE (pas de False sur panne serveur)."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(500))

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.verify_company_exists(123)

    @pytest.mark.asyncio
    async def test_propagates_on_timeout(self):
        """Un timeout (non HTTPStatusError) n'est pas capturé -> propagé."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(httpx.TimeoutException):
            await adapter.verify_company_exists(123)


class TestCreateProvider:
    """``create_provider`` : id valide -> int, id manquant -> BoondCrmError."""

    @pytest.mark.asyncio
    async def test_returns_int_id_on_success(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": 456}})

        result = await adapter.create_provider(
            company_name="ACME",
            siren="123456789",
            contact_email="contact@acme.test",
        )

        assert result == 456
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_coerces_string_id_to_int(self):
        """Boond renvoie souvent l'id en chaîne : ``_require_created_id`` le caste."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "789"}})

        result = await adapter.create_provider(
            company_name="ACME",
            siren="123456789",
            contact_email="contact@acme.test",
        )

        assert result == 789

    @pytest.mark.asyncio
    async def test_raises_when_no_id(self):
        """2xx sans ``data.id`` -> BoondCrmError (au lieu de renvoyer un faux id)."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {}})

        with pytest.raises(BoondCrmError):
            await adapter.create_provider(
                company_name="ACME",
                siren="123456789",
                contact_email="contact@acme.test",
            )

    @pytest.mark.asyncio
    async def test_raises_when_id_is_zero(self):
        """``id == 0`` est falsy : doit lever BoondCrmError, pas retourner 0."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": 0}})

        with pytest.raises(BoondCrmError):
            await adapter.create_provider(
                company_name="ACME",
                siren="123456789",
                contact_email="contact@acme.test",
            )


class TestCreatePurchaseOrder:
    """``create_purchase_order`` : id valide -> int, id manquant -> BoondCrmError."""

    @pytest.mark.asyncio
    async def test_returns_int_id_on_success(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": 555}})

        result = await adapter.create_purchase_order(
            provider_id=12,
            positioning_id=34,
            reference="REF-1",
            amount=500.0,
        )

        assert result == 555

    @pytest.mark.asyncio
    async def test_raises_when_no_id(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {}})

        with pytest.raises(BoondCrmError):
            await adapter.create_purchase_order(
                provider_id=12,
                positioning_id=34,
                reference="REF-1",
                amount=500.0,
            )


class TestCreateContact:
    """``create_contact`` : id valide -> int, id manquant -> BoondCrmError."""

    @pytest.mark.asyncio
    async def test_returns_int_id_on_success(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": 321}})

        result = await adapter.create_contact(
            company_id=1,
            civility="M.",
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@acme.test",
            phone="+33600000000",
            job_title="Directeur",
        )

        assert result == 321

    @pytest.mark.asyncio
    async def test_raises_when_no_id(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {}})

        with pytest.raises(BoondCrmError):
            await adapter.create_contact(
                company_id=1,
                civility="M.",
                first_name="Jean",
                last_name="Dupont",
                email="jean.dupont@acme.test",
                phone="+33600000000",
                job_title="Directeur",
            )


class TestCreateBoondContract:
    """``create_boond_contract`` : id valide -> int, id manquant -> BoondCrmError."""

    @pytest.mark.asyncio
    async def test_returns_int_id_on_success(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": 909}})

        result = await adapter.create_boond_contract(
            resource_id=5,
            positioning_id=6,
            daily_rate=500.0,
            type_of=2,
        )

        assert result == 909

    @pytest.mark.asyncio
    async def test_raises_when_no_id(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {}})

        with pytest.raises(BoondCrmError):
            await adapter.create_boond_contract(
                resource_id=5,
                positioning_id=6,
                daily_rate=500.0,
                type_of=2,
            )


class TestGetCompanyInformation:
    """``get_company_information`` : la fiche réduite, None sur 404, propage sinon."""

    @pytest.mark.asyncio
    async def test_returns_identity_fields(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": {
                    "id": "123",
                    "type": "company",
                    "attributes": {
                        "name": "ACME SAS",
                        "state": 9,
                        "registrationNumber": "894 213 669 00012",
                        "vatNumber": "FR12894213669",
                        "town": "Paris",
                        "website": "ignored",
                    },
                }
            }
        )

        result = await adapter.get_company_information(123)

        assert result == {
            "id": 123,
            "name": "ACME SAS",
            "state": 9,
            "registration_number": "894 213 669 00012",
            "vat_number": "FR12894213669",
            "town": "Paris",
        }
        boond._make_request.assert_awaited_once_with("GET", "/companies/123/information")

    @pytest.mark.asyncio
    async def test_returns_none_only_on_404(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(404))

        assert await adapter.get_company_information(123) is None

    @pytest.mark.asyncio
    async def test_propagates_on_500(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(500))

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.get_company_information(123)


class TestUpdateCompanyInformation:
    """``update_company_information`` : l'identité collectée, jamais le nom ni l'état."""

    @pytest.mark.asyncio
    async def test_pushes_identity_fields_only(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "123"}})

        await adapter.update_company_information(
            company_id=123,
            postcode="75001",
            address="1 rue de la Paix",
            town="Paris",
            country="France",
            legal_status="SAS au capital de 1 000 €",
            registered_office="894 213 669 R.C.S. Paris",
            vat_number="FR12894213669",
            siret="89421366900012",
            ape_code="6202A",
        )

        boond._make_request.assert_awaited_once()
        method, path = boond._make_request.await_args.args
        payload = boond._make_request.await_args.kwargs["json"]
        assert (method, path) == ("PUT", "/companies/123/information")
        assert payload == {
            "data": {
                "attributes": {
                    "postcode": "75001",
                    "address": "1 rue de la Paix",
                    "town": "Paris",
                    "country": "France",
                    "legalStatus": "SAS au capital de 1 000 €",
                    "registeredOffice": "894 213 669 R.C.S. Paris",
                    "vatNumber": "FR12894213669",
                    "registrationNumber": "89421366900012",
                    "apeCode": "6202A",
                }
            }
        }
        assert "name" not in payload["data"]["attributes"]
        assert "state" not in payload["data"]["attributes"]

    @pytest.mark.asyncio
    async def test_skips_empty_values_and_noop_when_nothing(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={})

        await adapter.update_company_information(company_id=123, siret="", ape_code=None)

        boond._make_request.assert_not_awaited()


def _contact(contact_id: str, company_id: str | None, **emails) -> dict:
    item = {"id": contact_id, "type": "contact", "attributes": dict(emails)}
    if company_id is not None:
        item["relationships"] = {"company": {"data": {"id": company_id, "type": "company"}}}
    return item


class TestFindContactByEmail:
    """``find_contact_by_email`` : même adresse, même société, sinon rien."""

    @pytest.mark.asyncio
    async def test_matches_email_on_the_same_company(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": [
                    _contact("10", "999", email1="jean@acme.test"),
                    _contact("11", "123", email1="Jean@ACME.test"),
                ]
            }
        )

        result = await adapter.find_contact_by_email(123, " jean@acme.test ")

        assert result == 11
        boond._make_request.assert_awaited_once_with(
            "GET", "/contacts", params={"keywords": "jean@acme.test", "maxResults": 30}
        )

    @pytest.mark.asyncio
    async def test_matches_secondary_email(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": [_contact("12", "123", email1="pro@acme.test", email2="jean@acme.test")]
            }
        )

        assert await adapter.find_contact_by_email(123, "jean@acme.test") == 12

    @pytest.mark.asyncio
    async def test_never_attaches_a_contact_of_another_company(self):
        """Un homonyme chez un autre client, ou sans société, n'est pas rattaché."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": [
                    _contact("10", "999", email1="jean@acme.test"),
                    _contact("13", None, email1="jean@acme.test"),
                ]
            }
        )

        assert await adapter.find_contact_by_email(123, "jean@acme.test") is None

    @pytest.mark.asyncio
    async def test_no_request_without_email(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": []})

        assert await adapter.find_contact_by_email(123, "  ") is None
        boond._make_request.assert_not_awaited()
