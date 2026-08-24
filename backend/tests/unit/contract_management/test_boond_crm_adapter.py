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


class TestPositioningStatesDictionary:
    """L'échelle des états se lit dans le CRM, elle ne se suppose pas."""

    @pytest.mark.asyncio
    async def test_the_states_are_read_from_the_dictionary(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": [
                    {"id": "0", "attributes": {"value": "Positionné"}},
                    {"id": "1", "attributes": {"value": "Refus Client"}},
                    {"id": "2", "attributes": {"value": "Gagné"}},
                    {"id": "7", "attributes": {"value": "Gagné attente contrat"}},
                ]
            }
        )

        states = await adapter.positioning_states()

        assert boond._make_request.await_args.args == (
            "GET",
            "/application/dictionary/setting.state.positioning",
        )
        assert states == {
            0: "Positionné",
            1: "Refus Client",
            2: "Gagné",
            7: "Gagné attente contrat",
        }

    @pytest.mark.asyncio
    async def test_an_unreadable_dictionary_gives_nothing(self):
        """L'appelant décide quoi faire : ici, rien ne doit remonter en erreur."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(404))

        assert await adapter.positioning_states() == {}

    @pytest.mark.asyncio
    async def test_an_unparsable_entry_is_skipped(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={
                "data": [
                    {"id": "deux", "attributes": {"value": "Gagné"}},
                    {"id": "2", "attributes": {"value": "Gagné"}},
                ]
            }
        )

        assert await adapter.positioning_states() == {2: "Gagné"}


class TestPositioningState:
    """Le passage à « Gagné » est ce qui fait naître la prestation."""

    @pytest.mark.asyncio
    async def test_the_state_is_written_at_the_positioning_own_address(self):
        """Un positionnement n'a pas d'onglet « information » : cette adresse répond 404.

        Sa lecture le disait déjà — `GET /positionings/{id}` —, comme pour les
        prestations. Les candidats, sociétés et besoins, eux, ont bien cet onglet.
        """
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "538"}})

        await adapter.update_positioning_state(538, 1)

        method, path = boond._make_request.await_args.args[:2]
        assert (method, path) == ("PUT", "/positionings/538")

    @pytest.mark.asyncio
    async def test_only_the_state_is_sent(self):
        """Dates, tarif de vente et jours restent ceux du commercial."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "538"}})

        await adapter.update_positioning_state(538, 1)

        data = boond._make_request.await_args.kwargs["json"]["data"]
        assert data == {"type": "positioning", "id": "538", "attributes": {"state": 1}}

    @pytest.mark.asyncio
    async def test_the_state_boond_confirms_is_returned(self):
        """Une réponse en 200 ne dit pas que le changement a été pris."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            return_value={"data": {"id": "538", "attributes": {"state": 7}}}
        )

        assert await adapter.update_positioning_state(538, 1) == 7

    @pytest.mark.asyncio
    async def test_a_response_without_state_says_nothing(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "538"}})

        assert await adapter.update_positioning_state(538, 1) is None


def _purchase_defaults(**relationship_overrides) -> dict:
    """Réponse type de ``GET /purchases/default?delivery=...``.

    Reprise d'une réponse réelle du CRM. Boond y compose un achat vide déjà
    accordé au contexte de la prestation — responsable, agence, pôle, projet,
    société et contact du client — et y **pré-calcule le montant** depuis les
    conditions de la prestation : ``quantity`` x ``amountExcludingTax``, ce
    dernier étant unitaire.

    Elle porte aussi quatre clés que le schéma d'écriture ignore et qui font
    échouer un ``POST`` en ``additionalProperties: false`` : ``_metadata``,
    ``createPayments``, ``statePayments`` et la relation ``order``.
    """
    relationships = {
        "mainManager": {"data": {"type": "resource", "id": "12"}},
        "agency": {"data": {"type": "agency", "id": "1"}},
        "pole": {"data": {"type": "pole", "id": "3"}},
        "project": {"data": {"type": "project", "id": "567"}},
        "company": {"data": {"type": "company", "id": "89"}},
        "contact": {"data": {"type": "contact", "id": "90"}},
        "delivery": {"data": {"type": "delivery", "id": "1234"}},
        "billingDetail": {"data": None},
        "createdBy": {"data": None},
        "order": {"data": None},
        "files": {"data": []},
    }
    relationships.update(relationship_overrides)
    return {
        "data": {
            "id": "0",
            "type": "purchase",
            "attributes": {
                "typeOf": 1,
                "state": 1,
                "subscription": 1,
                "currency": 0,
                "currencyAgency": 0,
                "exchangeRate": 1,
                "exchangeRateAgency": 1,
                "paymentTerm": 12,
                "paymentMethod": 0,
                "taxRate": 20,
                "taxRates": [20],
                "date": "2026-08-24",
                "startDate": "2026-07-06",
                "endDate": "2026-12-31",
                "quantity": 6,
                "amountExcludingTax": 12285,
                # Calculés par Boond, jamais réécrits.
                "amountIncludingTax": 14742,
                "totalAmountExcludingTax": 73710,
                "totalAmountIncludingTax": 88452,
                # Hors schéma d'écriture.
                "createPayments": 0,
                "statePayments": None,
                "_metadata": {
                    "version": "9.1.83.1",
                    "isLogged": True,
                    "language": "fr",
                    "login": "adv@geminiconsulting.fr",
                    "customer": "gemini",
                },
            },
            "relationships": relationships,
        },
        "included": [{"type": "delivery", "id": "1234"}],
    }


def _purchase_calls(boond: AsyncMock) -> tuple[dict, dict]:
    """Renvoie les paramètres du pré-remplissage et le corps de la création."""
    prefill, creation = boond._make_request.await_args_list
    assert prefill.args[:2] == ("GET", "/purchases/default")
    assert creation.args[:2] == ("POST", "/purchases")
    return prefill.kwargs["params"], creation.kwargs["json"]["data"]


class TestSupplierPurchaseCreation:
    """L'achat fournisseur : pré-remplissage Boond, puis `POST /purchases`.

    `/purchase-orders` n'existe pas dans l'API BoondManager — il répondait 404
    et faisait échouer tout le report d'un bon de commande. Le corps part de
    `GET /purchases/default`, qui accorde prestation, projet, société et agence
    entre eux : les composer à la main est la cause classique des 422.
    """

    @pytest.mark.asyncio
    async def test_the_purchase_is_prefilled_from_its_delivery(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        purchase_id = await adapter.create_supplier_purchase(
            delivery_id=1234, title="GEM-BC-001 - Développeur Python"
        )

        assert purchase_id == 666
        params, data = _purchase_calls(boond)
        assert params == {"delivery": "1234"}
        assert data["type"] == "purchase"
        # Le contexte composé par Boond est repris.
        assert data["attributes"]["currency"] == 0
        assert data["attributes"]["paymentTerm"] == 12
        assert data["relationships"]["project"]["data"]["id"] == "567"
        assert data["relationships"]["agency"]["data"]["id"] == "1"

    @pytest.mark.asyncio
    async def test_the_delivery_relationship_carries_the_delivery_type(self):
        """La doc décrit cette relation avec `type: "project"` : c'est une coquille."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=797, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        assert data["relationships"]["delivery"] == {"data": {"type": "delivery", "id": "797"}}

    @pytest.mark.asyncio
    async def test_empty_relationships_are_dropped(self):
        """Renvoyer une relation à `null` ferait échouer la création."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        assert "billingDetail" not in data["relationships"]

    @pytest.mark.asyncio
    async def test_the_mission_conditions_are_written_on_the_purchase(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(
            delivery_id=1234,
            title="GEM-BC-001 - Développeur Python",
            reference="GEM-BC-001",
            start_date="2026-09-01",
            end_date="2027-02-28",
        )

        _, data = _purchase_calls(boond)
        assert data["attributes"]["title"] == "GEM-BC-001 - Développeur Python"
        assert data["attributes"]["reference"] == "GEM-BC-001"
        assert data["attributes"]["startDate"] == "2026-09-01"
        assert data["attributes"]["endDate"] == "2027-02-28"

    @pytest.mark.asyncio
    async def test_the_purchase_date_is_the_start_of_the_period(self):
        """Le pré-remplissage y met le jour même : l'achat se rangerait dans le mauvais exercice."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(
            delivery_id=1234, title="GEM-BC-001", start_date="2026-09-01"
        )

        _, data = _purchase_calls(boond)
        assert data["attributes"]["date"] == "2026-09-01"

    @pytest.mark.asyncio
    async def test_the_prefilled_amount_is_never_overwritten(self):
        """Boond compte `quantity` x `amountExcludingTax`, ce dernier **unitaire**.

        Y poser le total du bon de commande le faisait multiplier une seconde
        fois : 18 jours à 500 € s'enregistraient à 162 000 € au lieu de 9 000.
        Le pré-remplissage dérive de la prestation, que le report vient de
        recaler — ses deux termes s'accordent déjà.
        """
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        assert data["attributes"]["quantity"] == 6
        assert data["attributes"]["amountExcludingTax"] == 12285

    @pytest.mark.asyncio
    async def test_keys_outside_the_write_schema_are_dropped(self):
        """`POST /purchases` est en `additionalProperties: false`.

        `_metadata` est le plus gênant : il porte le login de l'appelant et le
        nom du compte Boond, que l'on renverrait à l'expéditeur.
        """
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        for hors_schema in ("_metadata", "createPayments", "statePayments"):
            assert hors_schema not in data["attributes"]
        assert "order" not in data["relationships"]

    @pytest.mark.asyncio
    async def test_the_computed_totals_are_left_to_boond(self):
        """Les dicter ne peut que contredire le produit que Boond calcule lui-même."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        for calcule in (
            "amountIncludingTax",
            "totalAmountExcludingTax",
            "totalAmountIncludingTax",
        ):
            assert calcule not in data["attributes"]

    @pytest.mark.asyncio
    async def test_a_supplier_outside_vat_is_purchased_without_it(self):
        """Un fournisseur non assujetti facture sans TVA : le TTC serait gonflé."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(
            delivery_id=1234, title="GEM-BC-001", vat_liable=False
        )

        _, data = _purchase_calls(boond)
        assert data["attributes"]["taxRate"] == 0
        assert data["attributes"]["taxRates"] == [0]

    @pytest.mark.asyncio
    async def test_a_supplier_liable_to_vat_keeps_the_prefilled_rate(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        _, data = _purchase_calls(boond)
        assert data["attributes"]["taxRate"] == 20

    @pytest.mark.asyncio
    async def test_a_prefill_without_amount_creates_nothing(self):
        """Un achat à 0 € passerait inaperçu ; l'absence d'achat est signalée à l'ADV."""
        adapter, boond = _make_adapter()
        prefill = _purchase_defaults()
        prefill["data"]["attributes"]["amountExcludingTax"] = 0
        boond._make_request = AsyncMock(side_effect=[prefill, {"data": {"id": "666"}}])

        with pytest.raises(BoondCrmError):
            await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")

        assert boond._make_request.await_count == 1

    @pytest.mark.asyncio
    async def test_the_supplier_replaces_the_client_company_and_its_contact(self):
        """Un achat se paie au fournisseur : le contact du client n'y a plus sa place."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(
            delivery_id=1234, title="GEM-BC-001", provider_id=777
        )

        _, data = _purchase_calls(boond)
        assert data["relationships"]["company"] == {"data": {"type": "company", "id": "777"}}
        assert "contact" not in data["relationships"]

    @pytest.mark.asyncio
    async def test_the_supplier_contact_is_used_when_known(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {"id": "666"}}])

        await adapter.create_supplier_purchase(
            delivery_id=1234,
            title="GEM-BC-001",
            provider_id=777,
            provider_contact_id=2864,
        )

        _, data = _purchase_calls(boond)
        assert data["relationships"]["contact"] == {"data": {"type": "contact", "id": "2864"}}

    @pytest.mark.asyncio
    async def test_a_prefill_already_on_the_supplier_keeps_its_contact(self):
        """Boond a déjà désigné le fournisseur : son contact est le bon."""
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(
            side_effect=[
                _purchase_defaults(
                    company={"data": {"type": "company", "id": "777"}},
                    contact={"data": {"type": "contact", "id": "2864"}},
                ),
                {"data": {"id": "666"}},
            ]
        )

        await adapter.create_supplier_purchase(
            delivery_id=1234, title="GEM-BC-001", provider_id=777
        )

        _, data = _purchase_calls(boond)
        assert data["relationships"]["contact"] == {"data": {"type": "contact", "id": "2864"}}

    @pytest.mark.asyncio
    async def test_a_creation_without_id_is_an_error(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=[_purchase_defaults(), {"data": {}}])

        with pytest.raises(BoondCrmError):
            await adapter.create_supplier_purchase(delivery_id=1234, title="GEM-BC-001")


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


class TestConsultantExistence:
    """``candidate_exists`` / ``resource_exists`` : mêmes règles que pour une société.

    Elles décident si un consultant doit être converti ou pris tel quel :
    conclure à l'absence sur une panne ferait convertir une ressource, ce que
    BoondManager refuse.
    """

    @pytest.mark.asyncio
    async def test_a_candidate_is_looked_up_on_its_own_endpoint(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "4242"}})

        assert await adapter.candidate_exists(4242) is True
        assert boond._make_request.await_args.args[1] == "/candidates/4242"

    @pytest.mark.asyncio
    async def test_a_resource_is_looked_up_on_its_own_endpoint(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "9001"}})

        assert await adapter.resource_exists(9001) is True
        assert boond._make_request.await_args.args[1] == "/resources/9001"

    @pytest.mark.asyncio
    async def test_only_a_404_means_absent(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(404))

        assert await adapter.candidate_exists(4242) is False
        assert await adapter.resource_exists(4242) is False

    @pytest.mark.asyncio
    async def test_a_server_failure_is_propagated(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(side_effect=_http_status_error(500))

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.candidate_exists(4242)


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
