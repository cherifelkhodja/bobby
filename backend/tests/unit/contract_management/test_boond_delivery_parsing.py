"""Lecture d'une prestation BoondManager.

Le corps de test est une réponse réelle de l'API (prestation 797, renouvelée
le 2026-08-21), réduite à ce que l'adapter exploite. Elle sert de garde-fou :
si Boond change la forme de ses réponses, ce test le dit avant la production.
"""

from unittest.mock import AsyncMock

import pytest

from app.contract_management.infrastructure.adapters.boond_crm_adapter import BoondCrmAdapter

DELIVERY_RESPONSE = {
    "data": {
        "id": "797",
        "type": "delivery",
        "attributes": {
            "creationDate": "2026-08-21T19:19:52+0200",
            "startDate": "2020-07-01",
            "endDate": "2020-11-08",
            "title": "Historique",
            "state": 4,
            "typeOf": 0,
            "averageDailyPriceExcludingTax": 600,
            "averageDailyCost": 745.7142857143,
            "averageDailyContractCost": 745.7142857143,
            "numberOfDaysInvoicedOrQuantity": 0,
            "numberOfDaysFree": 0,
        },
        "relationships": {
            "project": {"data": {"id": "18", "type": "project"}},
            "dependsOn": {"data": {"id": "42", "type": "resource"}},
            "contract": {"data": {"id": "264", "type": "contract"}},
            "purchase": {"data": None},
            "master": {"data": None},
        },
    },
    "included": [
        {
            "id": "19",
            "type": "opportunity",
            "attributes": {"reference": "AO19", "title": "Expert MIM"},
        },
        {"id": "33", "type": "company", "attributes": {"name": "Pierre et Vacances SA"}},
        {
            "id": "18",
            "type": "project",
            "attributes": {"reference": "Expert MIM"},
            "relationships": {
                "mainManager": {"data": {"id": "2", "type": "resource"}},
                "opportunity": {"data": {"id": "19", "type": "opportunity"}},
                "company": {"data": {"id": "33", "type": "company"}},
                "contact": {"data": {"id": "49", "type": "contact"}},
            },
        },
        {
            "id": "42",
            "type": "resource",
            "attributes": {"firstName": "Imed", "lastName": "BOUKHAF", "typeOf": 0},
        },
    ],
}


def _make_adapter(response) -> BoondCrmAdapter:
    boond_client = AsyncMock()
    boond_client._make_request = AsyncMock(return_value=response)
    return BoondCrmAdapter(boond_client)


class TestGetDelivery:
    """Correspondance entre la prestation Boond et le bon de commande."""

    @pytest.mark.asyncio
    async def test_reads_the_period_and_the_rates(self):
        """Prix de vente et coût sont deux notions distinctes, comme TJM et CJM."""
        delivery = await _make_adapter(DELIVERY_RESPONSE).get_delivery(797)

        assert delivery["start_date"] == "2020-07-01"
        assert delivery["end_date"] == "2020-11-08"
        assert delivery["sale_daily_rate"] == 600
        assert delivery["purchase_daily_rate"] == 745.7142857143

    @pytest.mark.asyncio
    async def test_reads_the_quantities_including_free_days(self):
        """Jours vendus et gratuité négociés sur la prestation priment sur le positionnement."""
        delivery = await _make_adapter(DELIVERY_RESPONSE).get_delivery(797)

        assert delivery["days_sold"] == 0
        assert delivery["free_days"] == 0

    @pytest.mark.asyncio
    async def test_resolves_the_project_chain(self):
        """Le projet porte le client final, le besoin et le commercial."""
        delivery = await _make_adapter(DELIVERY_RESPONSE).get_delivery(797)

        assert delivery["project_id"] == 18
        assert delivery["client_id"] == 33
        assert delivery["client_name"] == "Pierre et Vacances SA"
        assert delivery["need_id"] == 19
        assert delivery["main_manager_id"] == 2

    @pytest.mark.asyncio
    async def test_reads_the_attached_resource_and_contract(self):
        """Le contrat rattaché évite d'en créer un second sur la ressource."""
        delivery = await _make_adapter(DELIVERY_RESPONSE).get_delivery(797)

        assert delivery["resource_id"] == 42
        assert delivery["contract_id"] == 264
        # Prestation renouvelée sans achat : la relation est explicitement nulle.
        assert delivery["purchase_id"] is None

    @pytest.mark.asyncio
    async def test_a_delivery_without_project_stays_readable(self):
        """Une prestation sans projet ne fait pas échouer la lecture."""
        response = {
            "data": {
                "id": "800",
                "type": "delivery",
                "attributes": {"startDate": "2026-09-01", "numberOfDaysFree": 2},
                "relationships": {},
            }
        }
        delivery = await _make_adapter(response).get_delivery(800)

        assert delivery["free_days"] == 2
        assert delivery["client_name"] is None
        assert delivery["need_id"] is None

    @pytest.mark.asyncio
    async def test_an_api_failure_returns_none(self):
        """Une prestation illisible ne fait pas échouer la création d'un BDC."""
        boond_client = AsyncMock()
        boond_client._make_request = AsyncMock(side_effect=RuntimeError("Boond 500"))

        assert await BoondCrmAdapter(boond_client).get_delivery(797) is None
