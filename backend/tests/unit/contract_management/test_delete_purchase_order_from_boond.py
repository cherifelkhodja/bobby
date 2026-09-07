"""Tests de la suppression, dans BoondManager, de ce qu'un report y a créé.

Outil de test : il sert à rejouer un report sans laisser d'achats et de
contrats fantômes derrière soi. Ce qui est vérifié ici : l'ordre inverse de la
création, le sort d'un identifiant dont la suppression a échoué, et ce que le
compte rendu dit à l'ADV.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.delete_purchase_order_from_boond import (
    DeletePurchaseOrderFromBoondUseCase,
)
from app.contract_management.domain.entities.purchase_order import PurchaseOrder
from app.contract_management.domain.exceptions import PurchaseOrderNotFoundError
from app.contract_management.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)


def _pushed_po(**overrides) -> PurchaseOrder:
    defaults = {
        "provisional_reference": "PROV-BDC-2026-001",
        "reference": "GEM-BDC-001",
        "status": PurchaseOrderStatus.SIGNED,
        "third_party_id": uuid4(),
        "boond_positioning_id": 41,
        "boond_consultant_id": 9001,
        "boond_consultant_type": "resource",
        "boond_delivery_id": 797,
        "boond_contract_id": 555,
        "boond_purchase_order_id": 666,
        "purchase_daily_rate": Decimal("500"),
        "days_sold": Decimal("20"),
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 2, 28),
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _make_use_case(po):
    po_repo = AsyncMock()
    po_repo.get_by_id = AsyncMock(return_value=po)
    po_repo.save = AsyncMock(side_effect=lambda entity: entity)

    crm = AsyncMock()
    crm.delete_supplier_purchase = AsyncMock(return_value=True)
    crm.delete_boond_contract = AsyncMock(return_value=True)
    crm.delete_delivery = AsyncMock(return_value=True)
    crm.delete_resource = AsyncMock(return_value=True)
    crm.update_positioning_state = AsyncMock()
    # Le positionnement n'a jamais perdu de vue le candidat d'origine.
    crm.get_positioning = AsyncMock(
        return_value={"candidate_id": 2398, "consultant_type": "candidate"}
    )

    use_case = DeletePurchaseOrderFromBoondUseCase(
        purchase_order_repository=po_repo, crm_service=crm
    )
    return use_case, crm


class TestSuppression:
    """Ce qui part du CRM, et dans quel ordre."""

    @pytest.mark.asyncio
    async def test_tout_est_supprime_a_l_envers_de_la_creation(self):
        """L'achat pend à la prestation : il part le premier."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)

        result, report = await use_case.execute(po.id)

        crm.delete_supplier_purchase.assert_awaited_once_with(666)
        crm.delete_boond_contract.assert_awaited_once_with(555)
        crm.delete_delivery.assert_awaited_once_with(797)
        assert result.boond_purchase_order_id is None
        assert result.boond_contract_id is None
        assert result.boond_delivery_id is None
        assert report[0].startswith("Achat #666")

    @pytest.mark.asyncio
    async def test_le_positionnement_repasse_en_attente_de_contrat(self):
        """Le laisser à « Gagné » ferait croire la mission gagnée sans prestation."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)

        _, report = await use_case.execute(po.id)

        crm.update_positioning_state.assert_awaited_once_with(41, 7)
        assert any("Gagné attente contrat" in ligne for ligne in report)

    @pytest.mark.asyncio
    async def test_le_report_peut_ensuite_etre_rejoue(self):
        """L'erreur du report précédent ne doit pas rester affichée."""
        po = _pushed_po(boond_sync_error="Achat fournisseur non créé")
        use_case, _ = _make_use_case(po)

        result, _ = await use_case.execute(po.id)

        assert result.boond_sync_error is None

    @pytest.mark.asyncio
    async def test_seul_ce_qui_existe_est_supprime(self):
        po = _pushed_po(boond_purchase_order_id=None, boond_contract_id=None)
        use_case, crm = _make_use_case(po)

        _, report = await use_case.execute(po.id)

        crm.delete_supplier_purchase.assert_not_awaited()
        crm.delete_boond_contract.assert_not_awaited()
        crm.delete_delivery.assert_awaited_once_with(797)
        assert len(report) == 3  # prestation, positionnement, ressource


class TestEchecs:
    """Un objet qui résiste ne doit pas être oublié."""

    @pytest.mark.asyncio
    async def test_un_identifiant_non_supprime_est_conserve(self):
        """L'effacer ferait créer un doublon au report suivant."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)
        crm.delete_boond_contract = AsyncMock(side_effect=RuntimeError("Boond 403"))

        result, report = await use_case.execute(po.id)

        assert result.boond_contract_id == 555
        assert any("Contrat #555 : suppression refusée" in ligne for ligne in report)

    @pytest.mark.asyncio
    async def test_un_echec_n_empeche_pas_les_autres_suppressions(self):
        po = _pushed_po()
        use_case, crm = _make_use_case(po)
        crm.delete_supplier_purchase = AsyncMock(side_effect=RuntimeError("Boond 403"))

        result, _ = await use_case.execute(po.id)

        assert result.boond_purchase_order_id == 666
        assert result.boond_contract_id is None
        assert result.boond_delivery_id is None

    @pytest.mark.asyncio
    async def test_un_positionnement_non_remis_est_signale(self):
        po = _pushed_po()
        use_case, crm = _make_use_case(po)
        crm.update_positioning_state = AsyncMock(side_effect=RuntimeError("Boond 500"))

        _, report = await use_case.execute(po.id)

        assert any("à remettre à la main" in ligne for ligne in report)


class TestComptesRendus:
    """Ce que l'ADV lit après coup."""

    @pytest.mark.asyncio
    async def test_rien_a_supprimer_est_dit_tel_quel(self):
        po = _pushed_po(
            boond_purchase_order_id=None,
            boond_contract_id=None,
            boond_delivery_id=None,
            boond_consultant_type="candidate",
        )
        use_case, crm = _make_use_case(po)

        _, report = await use_case.execute(po.id)

        assert report == ["Rien n'avait été poussé dans BoondManager."]
        crm.update_positioning_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_la_ressource_est_supprimee(self):
        """Elle ne se reconvertit pas en candidat, mais elle s'efface."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)

        _, report = await use_case.execute(po.id)

        crm.delete_resource.assert_awaited_once_with(9001)
        assert any("Ressource #" in ligne and "supprimée" in ligne for ligne in report)

    @pytest.mark.asyncio
    async def test_le_bon_de_commande_repointe_sur_le_candidat(self):
        """Sans quoi il désignerait une ressource effacée."""
        po = _pushed_po()
        use_case, _ = _make_use_case(po)

        result, _ = await use_case.execute(po.id)

        assert result.boond_consultant_id == 2398
        assert result.boond_consultant_type == "candidate"

    @pytest.mark.asyncio
    async def test_un_candidat_illisible_detache_le_consultant(self):
        """Mieux vaut un consultant à ressaisir qu'un renvoi vers le vide."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)
        crm.get_positioning = AsyncMock(return_value=None)

        result, report = await use_case.execute(po.id)

        assert result.boond_consultant_id is None
        assert any("Consultant détaché" in ligne for ligne in report)

    @pytest.mark.asyncio
    async def test_l_ordre_est_celui_de_la_creation_a_l_envers(self):
        """Chaque objet repose sur le précédent : achat, prestation, contrat, ressource."""
        po = _pushed_po()
        use_case, crm = _make_use_case(po)
        appels: list[str] = []
        for nom in (
            "delete_supplier_purchase",
            "delete_delivery",
            "delete_boond_contract",
            "delete_resource",
        ):
            setattr(crm, nom, AsyncMock(side_effect=lambda _id, n=nom: appels.append(n)))

        await use_case.execute(po.id)

        assert appels == [
            "delete_supplier_purchase",
            "delete_delivery",
            "delete_boond_contract",
            "delete_resource",
        ]

    @pytest.mark.asyncio
    async def test_un_consultant_reste_candidat_ne_dit_rien(self):
        po = _pushed_po(boond_consultant_type="candidate")
        use_case, _ = _make_use_case(po)

        _, report = await use_case.execute(po.id)

        assert not any("candidat" in ligne for ligne in report)

    @pytest.mark.asyncio
    async def test_un_bon_de_commande_inconnu_est_une_erreur(self):
        po = _pushed_po()
        use_case, _ = _make_use_case(po)
        use_case._po_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(PurchaseOrderNotFoundError):
            await use_case.execute(po.id)
