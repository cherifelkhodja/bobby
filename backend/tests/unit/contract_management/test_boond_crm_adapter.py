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


class TestPurchaseCreation:
    """L'achat fournisseur : `POST /purchases`, type `purchase`.

    `/purchase-orders` n'existe pas dans l'API BoondManager — il répondait 404
    et faisait échouer tout le report d'un bon de commande.
    """

    @pytest.mark.asyncio
    async def test_the_purchase_is_posted_on_the_right_resource(self):
        adapter, boond = _make_adapter()
        boond._make_request = AsyncMock(return_value={"data": {"id": "666"}})

        purchase_id = await adapter.create_purchase_order(
            provider_id=777, positioning_id=41, reference="GEM-BC-001", amount=9000.0
        )

        assert purchase_id == 666
        method, path = boond._make_request.await_args.args[:2]
        assert (method, path) == ("POST", "/purchases")
        data = boond._make_request.await_args.kwargs["json"]["data"]
        assert data["type"] == "purchase"
        assert data["attributes"]["amountExcludingTax"] == 9000.0
        assert data["attributes"]["reference"] == "GEM-BC-001"


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
