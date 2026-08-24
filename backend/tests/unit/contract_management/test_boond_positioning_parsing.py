"""Lecture d'un positionnement BoondManager.

Le corps de test reprend la fiche POS537 (« Gagné attente contrat »), réduite à
ce que l'adapter exploite. Le positionnement porte lui aussi les deux taux, les
jours vendus et la gratuité : c'est la source de préremplissage d'un bon de
commande quand aucune prestation n'existe encore.
"""

from unittest.mock import AsyncMock

import pytest

from app.contract_management.infrastructure.adapters.boond_crm_adapter import BoondCrmAdapter

POSITIONING_RESPONSE = {
    "data": {
        "id": "537",
        "type": "positioning",
        "attributes": {
            "state": 7,
            "startDate": "2026-01-01",
            "endDate": "2026-12-31",
            # Tarif de vente journalier (HT) : le TJM, interne.
            "averageDailyPriceExcludingTax": 800,
            # Coût journalier moyen (HT/jour) : le CJM, imprimé sur le BDC.
            "averageDailyCost": 700,
            "numberOfDaysInvoicedOrQuantity": 210,
            "numberOfDaysFree": 1,
        },
        "relationships": {
            "opportunity": {"data": {"id": "1534", "type": "opportunity"}},
            "dependsOn": {"data": {"id": "4242", "type": "candidate"}},
            "delivery": {"data": None},
        },
    },
    "included": [
        {
            "id": "4242",
            "type": "candidate",
            "attributes": {"firstName": "Cherif", "lastName": "TEST"},
        },
    ],
}


def _make_adapter(response) -> BoondCrmAdapter:
    boond_client = AsyncMock()
    boond_client._make_request = AsyncMock(return_value=response)
    return BoondCrmAdapter(boond_client)


class TestGetPositioning:
    """Correspondance entre le positionnement Boond et le bon de commande."""

    @pytest.mark.asyncio
    async def test_reads_both_daily_rates(self):
        """Tarif de vente et coût journalier sont deux notions distinctes."""
        positioning = await _make_adapter(POSITIONING_RESPONSE).get_positioning(537)

        assert positioning["daily_rate"] == 700
        assert positioning["sale_daily_rate"] == 800

    @pytest.mark.asyncio
    async def test_reads_the_quantities_including_free_days(self):
        """Les jours gratuits saisis sur le positionnement ne sont pas perdus."""
        positioning = await _make_adapter(POSITIONING_RESPONSE).get_positioning(537)

        assert positioning["quantity"] == 210
        assert positioning["free_days"] == 1

    @pytest.mark.asyncio
    async def test_reads_the_period_the_state_and_the_consultant(self):
        """L'état ouvre le workflow, le consultant et le besoin l'alimentent."""
        positioning = await _make_adapter(POSITIONING_RESPONSE).get_positioning(537)

        assert positioning["state"] == 7
        assert positioning["start_date"] == "2026-01-01"
        assert positioning["end_date"] == "2026-12-31"
        assert positioning["need_id"] == 1534
        assert positioning["candidate_id"] == 4242
        assert positioning["consultant_type"] == "candidate"
        assert positioning["consultant_first_name"] == "Cherif"
        assert positioning["consultant_last_name"] == "TEST"

    @pytest.mark.asyncio
    async def test_an_api_failure_returns_none(self):
        """Un positionnement illisible ne fait pas échouer le webhook."""
        boond_client = AsyncMock()
        boond_client._make_request = AsyncMock(side_effect=RuntimeError("Boond 500"))

        assert await BoondCrmAdapter(boond_client).get_positioning(537) is None
