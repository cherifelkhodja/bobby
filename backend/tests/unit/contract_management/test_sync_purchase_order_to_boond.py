"""Tests de la synchronisation BoondManager d'un bon de commande signé."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.sync_purchase_order_to_boond import (
    SyncPurchaseOrderToBoondUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import PurchaseOrderBoondSyncError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _signed_po(**overrides) -> PurchaseOrder:
    defaults = {
        "provisional_reference": "PROV-BC-2026-001",
        "reference": "GEM-BC-001",
        "status": PurchaseOrderStatus.SIGNED,
        "third_party_id": uuid4(),
        "contract_request_id": uuid4(),
        "boond_positioning_id": 41,
        "boond_consultant_id": 4242,
        "boond_consultant_type": "candidate",
        "purchase_daily_rate": Decimal("500"),
        "days_sold": Decimal("20"),
        "free_days": Decimal("2"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _third_party(**overrides) -> SimpleNamespace:
    defaults = {
        "boond_provider_id": 777,
        "company_name": "AKEMA TECH",
        "boond_billing_contact_id": 2864,
        "boond_adv_contact_id": 2865,
        "boond_signatory_contact_id": 2866,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_use_case(po, *, provider_id=777, third_party_type="sous_traitant", third_party=None):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=po)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)

    framework = ContractRequest(
        provisional_reference="PROV-2026-001",
        status=ContractRequestStatus.ACTIVE,
        third_party_type=third_party_type,
    )
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=framework)

    tp_repo = AsyncMock()
    tp_repo.get_by_id = AsyncMock(
        return_value=third_party or _third_party(boond_provider_id=provider_id)
    )

    crm = AsyncMock()
    crm.resolve_resource_id = AsyncMock(return_value=None)
    crm.candidate_exists = AsyncMock(return_value=True)
    crm.resource_exists = AsyncMock(return_value=False)
    crm.convert_candidate_to_resource = AsyncMock(return_value=9001)
    crm.update_resource_administrative = AsyncMock()
    crm.update_positioning_state = AsyncMock()
    # États de positionnement tels que configurés dans le CRM : chaque entité
    # Boond a la sienne, et « Gagné » n'y vaut pas 1 — c'est « Refus Client ».
    crm.positioning_states = AsyncMock(
        return_value={
            0: "Positionné",
            1: "Refus Client",
            2: "Gagné",
            3: "CV Envoyé",
            5: "Refus Collaborateur",
            7: "Gagné attente contrat",
        }
    )
    crm.get_positioning = AsyncMock(return_value={"delivery_id": 797})
    crm.create_boond_contract = AsyncMock(return_value=555)
    crm.create_supplier_purchase = AsyncMock(return_value=666)
    crm.renew_delivery = AsyncMock(return_value={"id": 798, "purchase_id": 900, "contract_id": 264})
    crm.update_delivery = AsyncMock()

    use_case = SyncPurchaseOrderToBoondUseCase(
        purchase_order_repository=po_repo,
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        crm_service=crm,
        db=None,
    )
    return use_case, crm, po_repo


class TestPrerequisites:
    """Ce qu'il faut avant de pouvoir pousser dans Boond."""

    @pytest.mark.asyncio
    async def test_an_unsigned_order_can_be_pushed(self):
        """Le report n'attend pas la signature : le CRM sert pendant qu'elle circule."""
        po = _signed_po(status=PurchaseOrderStatus.GENERATED)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_awaited_once()
        crm.create_supplier_purchase.assert_awaited_once()
        # Rien n'est signé : le bon de commande reste où il en est.
        assert result.status == PurchaseOrderStatus.GENERATED

    @pytest.mark.asyncio
    async def test_a_cancelled_order_is_refused(self):
        po = _signed_po(status=PurchaseOrderStatus.CANCELLED)
        use_case, crm, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderBoondSyncError, match="annulé"):
            await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_incomplete_conditions_are_refused(self):
        """Sans CJM ni dates, le contrat Boond n'aurait rien à porter."""
        po = _signed_po(status=PurchaseOrderStatus.DRAFT, purchase_daily_rate=None, end_date=None)
        use_case, crm, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderBoondSyncError, match="CJM"):
            await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_the_client_side_data_does_not_hold_the_push_back(self):
        """Client final, société émettrice et intitulé ne montent pas dans Boond."""
        po = _signed_po(status=PurchaseOrderStatus.DRAFT, client_name=None, mission_title=None)
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_a_supplier_absent_from_boond_is_refused(self):
        """La société fournisseur naît à la signature du contrat cadre."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po, provider_id=None)

        with pytest.raises(PurchaseOrderBoondSyncError, match="société fournisseur"):
            await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_order_without_positioning_is_refused(self):
        po = _signed_po(boond_positioning_id=None)
        use_case, _, _ = _make_use_case(po)

        with pytest.raises(PurchaseOrderBoondSyncError, match="positionnement"):
            await use_case.execute(po.id)


class TestResourceResolution:
    """Le consultant doit être une ressource Boond."""

    @pytest.mark.asyncio
    async def test_a_candidate_is_converted(self):
        """Le bon de commande acte la mission : le candidat devient ressource."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_awaited_once_with(
            4242,
            state=3,
            # Sous-traitance : « Consultant Externe » côté Boond.
            state_reason_type_of=1,
            type_of=1,
        )
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 9001

    @pytest.mark.asyncio
    async def test_a_commercial_portage_consultant_gets_its_own_resource_type(self):
        """Le portage commercial a son type de ressource dans Boond (10)."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po, third_party_type="portage_commercial")

        await use_case.execute(po.id)

        assert crm.convert_candidate_to_resource.await_args.kwargs["type_of"] == 10
        # Le motif du changement d'état, lui, reste « externe ».
        assert crm.convert_candidate_to_resource.await_args.kwargs["state_reason_type_of"] == 1

    @pytest.mark.asyncio
    async def test_an_existing_resource_is_reused(self):
        """Un candidat déjà converti n'est pas converti une seconde fois."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.resolve_resource_id = AsyncMock(return_value=8500)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_not_awaited()
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 8500

    @pytest.mark.asyncio
    async def test_a_resource_consultant_is_used_as_is(self):
        po = _signed_po(boond_consultant_type="resource", boond_consultant_id=8888)
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.resolve_resource_id.assert_not_awaited()
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 8888

    @pytest.mark.asyncio
    async def test_a_failed_provider_link_does_not_stop_the_sync(self):
        """Le rattachement administratif est corrigeable à la main dans Boond."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.update_resource_administrative = AsyncMock(side_effect=RuntimeError("Boond 422"))

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        crm.create_supplier_purchase.assert_awaited_once()


class TestDelivery:
    """La prestation Boond est mise d'accord avec le bon de commande."""

    @pytest.mark.asyncio
    async def test_the_delivery_is_realigned_on_the_order(self):
        """Boond crée la prestation depuis le positionnement ; le BDC en fixe les conditions."""
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.update_delivery.assert_awaited_once()
        kwargs = crm.update_delivery.await_args.kwargs
        assert kwargs["delivery_id"] == 797
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"
        assert kwargs["days_sold"] == 20
        assert kwargs["free_days"] == 2
        assert kwargs["purchase_daily_rate"] == 500

    @pytest.mark.asyncio
    async def test_the_client_sale_price_is_left_alone(self):
        """Le prix de vente relève du commercial : un document d'achat n'y touche pas."""
        po = _signed_po(boond_delivery_id=797, sale_daily_rate=Decimal("800"))
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        assert "sale_daily_rate" not in crm.update_delivery.await_args.kwargs

    @pytest.mark.asyncio
    async def test_a_missing_delivery_is_created_by_winning_the_positioning(self):
        """Bobby ne crée pas de prestation : il fait gagner le positionnement, Boond la crée."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 2)
        assert result.boond_delivery_id == 797
        # Et la prestation ainsi créée est aussitôt recalée sur le bon de commande.
        assert crm.update_delivery.await_args.kwargs["delivery_id"] == 797

    @pytest.mark.asyncio
    async def test_the_positioning_is_won_even_with_a_delivery_in_place(self):
        """Une prestation existe dès « Gagné attente contrat » : elle ne prouve rien.

        S'en remettre à son absence laissait la mission en attente dans le CRM
        une fois le report passé.
        """
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 2)
        # La prestation connue reste la sienne : rien n'est créé par-dessus.
        assert result.boond_delivery_id == 797

    @pytest.mark.asyncio
    async def test_a_state_that_did_not_take_is_reported(self):
        """Boond peut accepter la demande sans l'appliquer : cela doit se voir."""
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.get_positioning = AsyncMock(return_value={"delivery_id": 797, "state": 7})

        result = await use_case.execute(po.id)

        assert "l'état est resté à 7" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_state_ignored_outright_is_named_as_such(self):
        """Boond renvoie déjà l'ancien état : l'écriture n'a pas été prise en compte."""
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.update_positioning_state = AsyncMock(return_value=7)
        crm.get_positioning = AsyncMock(return_value={"delivery_id": 797, "state": 7})

        result = await use_case.execute(po.id)

        assert "n'a même pas été pris en compte" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_state_taken_then_undone_is_told_apart(self):
        """Boond a confirmé « Gagné », mais l'état est retombé : règle du CRM."""
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.update_positioning_state = AsyncMock(return_value=2)
        crm.get_positioning = AsyncMock(return_value={"delivery_id": 797, "state": 7})

        result = await use_case.execute(po.id)

        assert "l'état est resté à 7" in result.boond_sync_error
        assert "n'a même pas été pris en compte" not in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_state_that_took_says_nothing(self):
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.get_positioning = AsyncMock(return_value={"delivery_id": 797, "state": 2})

        result = await use_case.execute(po.id)

        assert result.boond_sync_error is None

    @pytest.mark.asyncio
    async def test_a_positioning_without_delivery_warns(self):
        """Gagné, mais aucune prestation rattachée : l'ADV doit le savoir."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        crm.get_positioning = AsyncMock(return_value={"delivery_id": None})

        result = await use_case.execute(po.id)

        assert "n'a pas rattaché de prestation" in result.boond_sync_error
        crm.update_delivery.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_failed_win_warns_without_failing_the_push(self):
        """Le contrat reste posé ; l'achat, lui, attend la prestation."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        crm.update_positioning_state = AsyncMock(side_effect=RuntimeError("Boond 500"))

        result = await use_case.execute(po.id)

        assert result.boond_contract_id == 555
        assert result.boond_purchase_order_id is None
        assert "non passé à « Gagné »" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_failed_alignment_warns_without_failing_the_push(self):
        po = _signed_po(boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.update_delivery = AsyncMock(side_effect=RuntimeError("Boond 500"))

        result = await use_case.execute(po.id)

        assert result.boond_purchase_order_id == 666
        assert "Prestation 797 non recalée" in result.boond_sync_error


class TestWonState:
    """Quel numéro vaut « Gagné » — la question qui a écrit un refus client.

    Chaque entité Boond a sa propre échelle d'états. L'état 1 est « Gagné »
    pour une opportunité, « Refus Client » pour un positionnement : le numéro
    ne se déduit pas, il se lit.
    """

    @pytest.mark.asyncio
    async def test_the_state_comes_from_the_crm_dictionary(self):
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 2)

    @pytest.mark.asyncio
    async def test_a_renamed_state_is_followed(self):
        """Les libellés sont réglés par l'administrateur du CRM : on les relit."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        crm.positioning_states = AsyncMock(return_value={4: "GAGNE", 9: "Gagné attente contrat"})

        await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 4)

    @pytest.mark.asyncio
    async def test_the_waiting_state_is_never_mistaken_for_it(self):
        """« Gagné attente contrat » commence pareil sans désigner le même état."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        crm.positioning_states = AsyncMock(return_value={7: "Gagné attente contrat"})

        result = await use_case.execute(po.id)

        crm.update_positioning_state.assert_not_awaited()
        assert "n'a pas pu être déterminé" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_an_unreadable_dictionary_falls_back_to_the_known_value(self):
        """S'abstenir priverait le report de sa prestation."""
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        crm.positioning_states = AsyncMock(return_value={})

        await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 2)

    @pytest.mark.asyncio
    async def test_the_administrator_setting_wins(self):
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        use_case._settings = AsyncMock()
        use_case._settings.get = AsyncMock(return_value="6")

        await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 6)
        crm.positioning_states.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unusable_setting_falls_back_to_the_dictionary(self):
        po = _signed_po(boond_delivery_id=None)
        use_case, crm, _ = _make_use_case(po)
        use_case._settings = AsyncMock()
        use_case._settings.get = AsyncMock(return_value="au choix")

        await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 2)


class TestProviderLink:
    """La ressource porte sa société fournisseur et son interlocuteur."""

    @pytest.mark.asyncio
    async def test_the_billing_contact_is_attached_to_the_resource(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.update_resource_administrative.await_args.kwargs
        assert kwargs["provider_company_id"] == 777
        assert kwargs["provider_contact_id"] == 2864

    @pytest.mark.asyncio
    async def test_the_adv_contact_takes_over_without_a_billing_one(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(
            po, third_party=_third_party(boond_billing_contact_id=None)
        )

        await use_case.execute(po.id)

        assert crm.update_resource_administrative.await_args.kwargs["provider_contact_id"] == 2865

    @pytest.mark.asyncio
    async def test_a_supplier_without_any_contact_is_still_linked(self):
        """La société seule vaut mieux qu'un rattachement refusé."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(
            po,
            third_party=_third_party(
                boond_billing_contact_id=None,
                boond_adv_contact_id=None,
                boond_signatory_contact_id=None,
            ),
        )

        await use_case.execute(po.id)

        kwargs = crm.update_resource_administrative.await_args.kwargs
        assert kwargs["provider_company_id"] == 777
        assert kwargs["provider_contact_id"] is None


class TestAlreadyAResource:
    """Le consultant est parfois déjà une ressource Boond."""

    @pytest.mark.asyncio
    async def test_a_consultant_declared_as_a_resource_is_used_as_is(self):
        po = _signed_po(boond_consultant_type="resource")
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_not_awaited()
        crm.candidate_exists.assert_not_awaited()
        assert crm.create_boond_contract.await_args.kwargs["resource_id"] == 4242

    @pytest.mark.asyncio
    async def test_an_id_that_is_not_a_candidate_but_a_resource_is_used_as_is(self):
        """Identifiant de ressource pris pour un candidat : le convertir échouerait."""
        po = _signed_po(boond_consultant_type="candidate")
        use_case, crm, _ = _make_use_case(po)
        crm.candidate_exists = AsyncMock(return_value=False)
        crm.resource_exists = AsyncMock(return_value=True)

        result = await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_not_awaited()
        assert result.boond_consultant_id == 4242
        assert result.boond_consultant_type == "resource"

    @pytest.mark.asyncio
    async def test_a_candidate_without_a_resource_is_still_converted(self):
        """Un candidat existant est converti : le numéro d'une ressource homonyme ne vaut rien.

        Candidats et ressources ont deux séries d'identifiants — se rabattre sur
        la ressource du même numéro rattacherait une autre personne.
        """
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_awaited_once()
        crm.resource_exists.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_an_unknown_consultant_is_reported(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.candidate_exists = AsyncMock(return_value=False)
        crm.resource_exists = AsyncMock(return_value=False)

        with pytest.raises(PurchaseOrderBoondSyncError, match="introuvable"):
            await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_not_awaited()


class TestResourceMemory:
    """La ressource résolue est retenue sur le bon de commande."""

    @pytest.mark.asyncio
    async def test_a_converted_candidate_becomes_a_resource_on_the_order(self):
        po = _signed_po()
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        assert result.boond_consultant_id == 9001
        assert result.boond_consultant_type == "resource"

    @pytest.mark.asyncio
    async def test_a_second_push_does_not_ask_boond_again(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)
        await use_case.execute(po.id)

        crm.convert_candidate_to_resource.assert_awaited_once()
        crm.resolve_resource_id.assert_awaited_once()


class TestBoondWrites:
    """Contenu des écritures Boond."""

    @pytest.mark.asyncio
    async def test_the_contract_carries_the_purchase_rate_and_dates(self):
        """Le contrat Boond porte le CJM d'achat, jamais le TJM de vente."""
        po = _signed_po(sale_daily_rate=Decimal("780"))
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.create_boond_contract.await_args.kwargs
        assert kwargs["daily_rate"] == 500.0
        assert kwargs["type_of"] == 2  # sous-traitant
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"

    @pytest.mark.asyncio
    async def test_the_contract_type_follows_the_third_party_type(self):
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po, third_party_type="portage_salarial")

        await use_case.execute(po.id)

        assert crm.create_boond_contract.await_args.kwargs["type_of"] == 6

    @pytest.mark.asyncio
    async def test_the_purchase_carries_the_billable_total(self):
        """Montant Boond = (jours vendus - gratuité) x CJM, sur les jours payés."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.create_supplier_purchase.await_args.kwargs
        assert kwargs["amount"] == 9000.0  # 18 x 500
        assert kwargs["quantity"] == 18.0  # 20 vendus - 2 gratuits
        assert kwargs["reference"] == "GEM-BC-001"
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"

    @pytest.mark.asyncio
    async def test_the_purchase_hangs_on_the_delivery_and_the_supplier(self):
        """L'achat se rattache à la prestation, et se paie au fournisseur."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.create_supplier_purchase.await_args.kwargs
        assert kwargs["delivery_id"] == 797
        assert kwargs["provider_id"] == 777
        assert kwargs["provider_contact_id"] == 2864  # contact facturation

    @pytest.mark.asyncio
    async def test_the_purchase_title_names_the_order_then_the_mission(self):
        """L'intitulé sert à retrouver l'achat dans Boond."""
        po = _signed_po(mission_title="Développeur Python senior")
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        title = crm.create_supplier_purchase.await_args.kwargs["title"]
        assert title == "GEM-BC-001 - Développeur Python senior"

    @pytest.mark.asyncio
    async def test_the_order_becomes_active(self):
        po = _signed_po()
        use_case, _, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        assert result.boond_contract_id == 555
        assert result.boond_purchase_order_id == 666
        assert result.boond_sync_error is None


class TestIdempotence:
    """Relancer une synchronisation ne duplique rien."""

    @pytest.mark.asyncio
    async def test_existing_boond_objects_are_not_recreated(self):
        po = _signed_po(
            status=PurchaseOrderStatus.ACTIVE,
            boond_contract_id=555,
            boond_purchase_order_id=666,
            boond_sync_error="Boond HTTP 500",
        )
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        crm.create_supplier_purchase.assert_not_awaited()
        assert result.boond_sync_error is None

    @pytest.mark.asyncio
    async def test_a_partial_sync_only_completes_what_is_missing(self):
        """Le contrat existe déjà, seul le bon de commande reste à créer."""
        po = _signed_po(boond_contract_id=555)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        crm.create_supplier_purchase.assert_awaited_once()
        assert result.boond_purchase_order_id == 666


class TestRenewals:
    """Une reconduction ne superpose pas un second contrat Boond."""

    @pytest.mark.asyncio
    async def test_a_renewal_uses_the_native_delivery_renewal(self):
        """Boond sait renouveler une prestation : on passe par là."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.renew_delivery.assert_awaited_once_with(797)
        assert result.boond_delivery_id == 798
        # L'achat créé par Boond est repris tel quel, sans en créer un second.
        crm.create_supplier_purchase.assert_not_awaited()
        assert result.boond_purchase_order_id == 900

    @pytest.mark.asyncio
    async def test_the_renewed_delivery_is_realigned_on_the_new_period(self):
        """Boond duplique à l'identique : sans recalage, les dates seraient fausses."""
        po = _signed_po(
            parent_purchase_order_id=uuid4(),
            boond_delivery_id=797,
            sale_daily_rate=Decimal("780"),
        )
        use_case, crm, _ = _make_use_case(po)

        await use_case.execute(po.id)

        kwargs = crm.update_delivery.await_args.kwargs
        assert kwargs["delivery_id"] == 798
        assert kwargs["start_date"] == "2026-09-01"
        assert kwargs["end_date"] == "2027-02-28"
        assert kwargs["days_sold"] == 20.0
        assert kwargs["free_days"] == 2.0
        assert kwargs["purchase_daily_rate"] == 500.0
        assert kwargs["sale_daily_rate"] == 780.0

    @pytest.mark.asyncio
    async def test_a_renewal_without_purchase_falls_back_to_creating_one(self):
        """Si Boond n'a pas produit l'achat, on le crée par la voie habituelle."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.renew_delivery = AsyncMock(return_value={"id": 798, "purchase_id": None})

        result = await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_awaited_once()
        assert result.boond_purchase_order_id == 666

    @pytest.mark.asyncio
    async def test_a_failed_realignment_warns_without_failing_the_sync(self):
        """La prestation et l'achat existent : l'échec du recalage n'invalide rien."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.update_delivery = AsyncMock(side_effect=RuntimeError("Boond 405"))

        result = await use_case.execute(po.id)

        assert result.status == PurchaseOrderStatus.ACTIVE
        assert "recaler dans BoondManager" in result.boond_sync_error
        assert "798" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_an_empty_renewal_response_is_an_error(self):
        """Sans prestation en retour, il n'y a rien à rattacher."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)
        crm.renew_delivery = AsyncMock(return_value=None)

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_renewal_without_a_delivery_goes_through_the_positioning(self):
        """Rien à renouveler : la prestation naît du positionnement, puis l'achat."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.renew_delivery.assert_not_awaited()
        crm.update_positioning_state.assert_awaited_once()
        assert result.boond_delivery_id == 797
        assert crm.create_supplier_purchase.await_args.kwargs["delivery_id"] == 797
        assert result.boond_purchase_order_id == 666

    @pytest.mark.asyncio
    async def test_a_renewal_does_not_create_a_second_contract(self):
        """Le consultant reste sous le même contrat de sous-traitance."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_boond_contract.assert_not_awaited()
        assert result.boond_contract_id is None

    @pytest.mark.asyncio
    async def test_a_renewal_still_creates_its_own_purchase_order(self):
        """Chaque période est un engagement d'achat distinct."""
        po = _signed_po(parent_purchase_order_id=uuid4())
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_awaited_once()
        assert result.boond_purchase_order_id == 666
        assert result.status == PurchaseOrderStatus.ACTIVE


class TestSupplierPurchase:
    """L'achat fournisseur pend à la prestation, jamais au vide."""

    @pytest.mark.asyncio
    async def test_no_delivery_means_no_purchase(self):
        """Le rattachement ne se fait qu'à la création : sans prestation, on s'abstient."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.get_positioning = AsyncMock(return_value={})

        result = await use_case.execute(po.id)

        crm.create_supplier_purchase.assert_not_awaited()
        assert result.boond_purchase_order_id is None
        assert "prestation" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_failed_purchase_does_not_undo_the_rest(self):
        """Ressource, contrat et prestation sont posés : on ne les rejoue pas pour un achat."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)
        crm.create_supplier_purchase = AsyncMock(side_effect=RuntimeError("Boond 422"))

        result = await use_case.execute(po.id)

        assert result.boond_contract_id == 555
        assert result.boond_delivery_id == 797
        assert result.boond_purchase_order_id is None
        assert result.status == PurchaseOrderStatus.ACTIVE
        assert "Achat fournisseur non créé" in result.boond_sync_error

    @pytest.mark.asyncio
    async def test_a_renewal_gets_its_purchase_from_boond(self):
        """Le renouvellement natif produit l'achat lui-même : rien à créer."""
        po = _signed_po(parent_purchase_order_id=uuid4(), boond_delivery_id=797)
        use_case, crm, _ = _make_use_case(po)

        result = await use_case.execute(po.id)

        crm.renew_delivery.assert_awaited_once_with(797)
        crm.create_supplier_purchase.assert_not_awaited()
        assert result.boond_purchase_order_id == 900


class TestErrorReporting:
    """Une erreur Boond doit rester lisible et rejouable."""

    @pytest.mark.asyncio
    async def test_the_error_is_stored_on_the_order(self):
        po = _signed_po()
        use_case, crm, po_repo = _make_use_case(po)
        crm.create_boond_contract = AsyncMock(side_effect=RuntimeError("Boond 422 unprocessable"))

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        assert "422" in po.boond_sync_error
        assert po.status == PurchaseOrderStatus.SIGNED
        po_repo.save.assert_awaited()

    @pytest.mark.asyncio
    async def test_an_http_response_is_summarised(self):
        """Le corps de la réponse Boond est repris, tronqué."""
        po = _signed_po()
        use_case, crm, _ = _make_use_case(po)

        class _BoondHttpError(Exception):
            """Erreur porteuse d'une réponse HTTP, comme celles de httpx."""

            response = SimpleNamespace(status_code=422, text="daily rate is required")

        failure = RuntimeError("wrapped")
        failure.__cause__ = _BoondHttpError()
        crm.create_boond_contract = AsyncMock(side_effect=failure)

        with pytest.raises(PurchaseOrderBoondSyncError):
            await use_case.execute(po.id)

        assert po.boond_sync_error == "Boond HTTP 422: daily rate is required"
