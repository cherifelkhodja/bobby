"""Tests for CreatePurchaseOrderFromPositioningUseCase."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.create_purchase_order import (
    CreatePurchaseOrderFromPositioningUseCase,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import (
    PositioningNotFoundError,
    PositioningStateMismatchError,
    PurchaseOrderAlreadyExistsError,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

POSITIONING = {
    "id": 41,
    "state": 7,
    "candidate_id": 4242,
    "consultant_type": "candidate",
    "consultant_first_name": "Camille",
    "consultant_last_name": "Norel",
    "resource_id": None,
    "need_id": 88,
    "need_title": "Développeur backend",
    "need_reference": "BPM043676",
    "manager_id": 12,
    "agency_id": 5,
    "client_name": "Client final",
    "project_id": 224,
    "daily_rate": "500",
    "sale_daily_rate": "800",
    "quantity": "20",
    "free_days": "1",
    "start_date": "2026-09-01",
    "end_date": "2027-02-28",
}


def _make_use_case(
    *,
    positioning=POSITIONING,
    existing=None,
    trigger_state="7",
    company_id=None,
    bobby_user=None,
):
    """Use case wired with fakes; returns it along with its repositories."""
    po_repo = AsyncMock()
    po_repo.get_by_positioning_id = AsyncMock(return_value=existing)
    po_repo.get_next_provisional_reference = AsyncMock(return_value="PROV-BDC-2026-001")
    po_repo.get_next_reference = AsyncMock(return_value="GEM-BDC-001")
    po_repo.save = AsyncMock(side_effect=lambda po: po)

    crm = AsyncMock()
    crm.get_positioning = AsyncMock(return_value=positioning)

    company_repo = AsyncMock()
    company_repo.get_company_by_boond_agency_id = AsyncMock(return_value=company_id)
    company_repo.get_company_code = AsyncMock(return_value="GEM")

    user_repo = AsyncMock()
    user_repo.get_by_boond_resource_id = AsyncMock(return_value=bobby_user)

    settings_service = AsyncMock()
    settings_service.get = AsyncMock(return_value=trigger_state)

    use_case = CreatePurchaseOrderFromPositioningUseCase(
        purchase_order_repository=po_repo,
        crm_service=crm,
        company_repository=company_repo,
        user_repository=user_repo,
        settings_service=settings_service,
    )
    return use_case, po_repo, crm, company_repo


class TestTriggerState:
    """Contrôle de l'état du positionnement."""

    @pytest.mark.asyncio
    async def test_creates_when_the_positioning_is_in_the_expected_state(self):
        """L'état 7 « Gagné attente contrat » ouvre un bon de commande."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        # Le numéro définitif n'arrive qu'à la génération du document.
        assert po.provisional_reference == "PROV-BDC-2026-001"
        assert po.reference is None
        assert po.display_reference == "PROV-BDC-2026-001"
        assert po.status == PurchaseOrderStatus.DRAFT

    @pytest.mark.asyncio
    async def test_refuses_any_other_state(self):
        """Un autre état ne déclenche rien."""
        use_case, po_repo, _, _ = _make_use_case(positioning={**POSITIONING, "state": 3})

        with pytest.raises(PositioningStateMismatchError) as exc:
            await use_case.execute(41)

        assert exc.value.state == 3
        assert exc.value.expected == 7
        po_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_the_expected_state_comes_from_the_settings(self):
        """L'état déclencheur est paramétrable sans redéploiement."""
        use_case, _, _, _ = _make_use_case(
            positioning={**POSITIONING, "state": 12}, trigger_state="12"
        )

        po = await use_case.execute(41)

        assert po.boond_positioning_id == 41

    @pytest.mark.asyncio
    async def test_falls_back_to_seven_when_the_setting_is_unreadable(self):
        """Une valeur de configuration illisible n'ouvre pas la porte à tout."""
        use_case, _, _, _ = _make_use_case(trigger_state="pas-un-entier")

        po = await use_case.execute(41)

        assert po.boond_positioning_id == 41

    @pytest.mark.asyncio
    async def test_unknown_positioning_is_reported(self):
        """Un positionnement introuvable dans Boond est signalé."""
        use_case, _, _, _ = _make_use_case(positioning=None)

        with pytest.raises(PositioningNotFoundError):
            await use_case.execute(41)


class TestIdempotence:
    """Un positionnement n'ouvre qu'un seul bon de commande."""

    @pytest.mark.asyncio
    async def test_refuses_a_second_purchase_order(self):
        """Rejouer le webhook ne crée pas de doublon."""
        existing = PurchaseOrder(
            provisional_reference="PROV-BDC-2026-001",
            reference="GEM-BDC-001",
            boond_positioning_id=41,
        )
        use_case, po_repo, _, _ = _make_use_case(existing=existing)

        with pytest.raises(PurchaseOrderAlreadyExistsError) as exc:
            await use_case.execute(41)

        assert exc.value.reference == "GEM-BDC-001"
        po_repo.save.assert_not_awaited()


class TestPrefill:
    """Préremplissage depuis le positionnement, le besoin et le consultant."""

    @pytest.mark.asyncio
    async def test_both_daily_rates_come_from_the_positioning(self):
        """averageDailyCost alimente le CJM, averageDailyPriceExcludingTax le TJM."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.purchase_daily_rate == Decimal("500")
        assert po.sale_daily_rate == Decimal("800")

    @pytest.mark.asyncio
    async def test_the_positioning_free_days_are_kept(self):
        """La gratuité saisie sur le positionnement suit dans le bon de commande."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.free_days == Decimal("1")
        assert po.billable_days == Decimal("19")

    @pytest.mark.asyncio
    async def test_mission_and_dates_come_from_boond(self):
        """Le besoin et le positionnement remplissent la mission."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.client_name == "Client final"
        assert po.mission_title == "Développeur backend"
        assert po.days_sold == Decimal("20")
        assert po.start_date == date(2026, 9, 1)
        assert po.end_date == date(2027, 2, 28)
        assert po.boond_need_id == 88

    @pytest.mark.asyncio
    async def test_consultant_identity_comes_from_the_positioning(self):
        """`dependsOn` dit la nature du consultant, `included` son nom."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.boond_consultant_id == 4242
        assert po.boond_consultant_type == "candidate"
        assert po.consultant_name == "Camille Norel"

    @pytest.mark.asyncio
    async def test_a_candidate_already_converted_points_at_its_resource(self):
        """En reconvertir un second créerait une ressource de plus."""
        use_case, _, _, _ = _make_use_case(positioning={**POSITIONING, "resource_id": 2870})

        po = await use_case.execute(41)

        assert po.boond_consultant_id == 2870
        assert po.boond_consultant_type == "resource"

    @pytest.mark.asyncio
    async def test_the_project_is_recorded(self):
        """L'achat s'y rattache, et c'est par lui que se retrouve la prestation."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.boond_project_id == 224

    @pytest.mark.asyncio
    async def test_the_supplier_is_left_to_be_chosen(self):
        """Un positionnement ne dit pas par quelle société le consultant est porté."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.needs_third_party
        assert po.third_party_id is None
        assert po.contract_request_id is None
        assert "le fournisseur" in po.missing_fields

    @pytest.mark.asyncio
    async def test_issuing_company_comes_from_the_boond_agency(self):
        """L'agence du besoin désigne la société émettrice."""
        company_id = uuid4()
        use_case, po_repo, _, company_repo = _make_use_case(company_id=company_id)

        po = await use_case.execute(41)

        company_repo.get_company_by_boond_agency_id.assert_awaited_once_with(5)
        assert po.company_id == company_id
        # La séquence de la société n'est pas entamée à ce stade.
        po_repo.get_next_reference.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_commercial_prefers_the_bobby_account(self):
        """Le commercial est résolu dans Bobby avant de retomber sur Boond."""
        bobby_user = AsyncMock()
        bobby_user.email = "commercial@geminiconsulting.fr"
        use_case, _, _, _ = _make_use_case(bobby_user=bobby_user)

        po = await use_case.execute(41)

        assert po.commercial_email == "commercial@geminiconsulting.fr"

    @pytest.mark.asyncio
    async def test_a_manager_without_a_bobby_account_leaves_it_empty(self):
        """Le positionnement ne porte pas l'email du commercial, seulement son numéro."""
        use_case, _, _, _ = _make_use_case()

        po = await use_case.execute(41)

        assert po.commercial_email is None


class TestBoondFailuresAreTolerated:
    """Une lecture Boond en échec ne doit pas bloquer la création."""

    @pytest.mark.asyncio
    async def test_a_positioning_without_its_context_still_creates_the_order(self):
        """`included` amputé : le bon de commande naît, à compléter par l'ADV."""
        use_case, _, _, _ = _make_use_case(
            positioning={**POSITIONING, "client_name": None, "need_title": None}
        )

        po = await use_case.execute(41)

        assert po.client_name is None
        assert po.consultant_name == "Camille Norel"

    @pytest.mark.asyncio
    async def test_consultant_lookup_failure_keeps_positioning_names(self):
        """Fiche consultant illisible : les noms du positionnement suffisent."""
        use_case, _, crm, _ = _make_use_case()
        crm.get_candidate_info = AsyncMock(side_effect=RuntimeError("Boond 500"))

        po = await use_case.execute(41)

        assert po.consultant_name == "Camille Norel"
        assert po.consultant_email is None

    @pytest.mark.asyncio
    async def test_a_positioning_without_need_is_supported(self):
        """Un positionnement sans besoin reste exploitable."""
        use_case, _, _, _ = _make_use_case(
            positioning={**POSITIONING, "need_id": None, "need_title": ""}
        )

        po = await use_case.execute(41)

        assert po.boond_need_id is None
        assert po.mission_title is None
