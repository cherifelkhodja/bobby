"""Tests for PushToCrmUseCase.

Verrouille deux correctifs :

1. **Transition d'archivage** : l'archivage relève du CRON. Ce use case ne tente
   ``ACTIVE -> ARCHIVED`` que si la demande est DÉJÀ ``ACTIVE``. Depuis ``SIGNED``,
   il ne transitionne pas (``SIGNED -> ARCHIVED`` serait invalide et levait une
   ``InvalidContractStatusError``).
2. **Bon de commande idempotent** : si ``contract.boond_purchase_order_id`` est
   déjà défini, ``create_purchase_order`` n'est PAS rappelé (pas de second BDC
   côté Boond sur un rejeu).

Tous les repos/services sont mockés en AsyncMock. CR et Contract sont construits
via leurs constructeurs réels ; le tiers (``tp``) est un MagicMock car le use
case ne lit que quelques attributs (``boond_provider_id``, ``company_name``…).
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.push_to_crm import PushToCrmUseCase
from app.contract_management.domain.entities.contract import Contract
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _make_contract(cr: ContractRequest, **overrides) -> Contract:
    """Build a Contract linked to the given contract request (real constructor)."""
    defaults = {
        "contract_request_id": cr.id,
        "third_party_id": cr.third_party_id or uuid4(),
        "reference": "XXX-CC-0001",
        "s3_key_draft": "drafts/contract.docx",
    }
    defaults.update(overrides)
    return Contract(**defaults)


def _build(cr: ContractRequest, contract: Contract, tp=None):
    """Wire the use case with AsyncMock repositories/services.

    ``save`` renvoie l'entité inchangée (side_effect identité) pour que
    ``execute`` retourne l'objet qu'on peut inspecter.
    """
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=cr)
    cr_repo.save = AsyncMock(side_effect=lambda entity: entity)

    contract_repo = AsyncMock()
    contract_repo.get_by_request_id = AsyncMock(return_value=contract)
    contract_repo.save = AsyncMock(side_effect=lambda entity: entity)

    tp_repo = AsyncMock()
    tp_repo.get_by_id = AsyncMock(return_value=tp)
    tp_repo.save = AsyncMock(side_effect=lambda entity: entity)

    crm = AsyncMock()

    uc = PushToCrmUseCase(
        contract_request_repository=cr_repo,
        contract_repository=contract_repo,
        third_party_repository=tp_repo,
        crm_service=crm,
    )
    return uc, cr_repo, contract_repo, tp_repo, crm


class TestArchiveTransition:
    """Le use case n'archive que depuis ACTIVE (fix SIGNED -> ARCHIVED invalide)."""

    @pytest.mark.asyncio
    async def test_active_is_archived(self):
        """Depuis ACTIVE, le push transitionne bien vers ARCHIVED."""
        cr = ContractRequest(
            provisional_reference="PROV-2026-0001",
            status=ContractRequestStatus.ACTIVE,
        )
        contract = _make_contract(cr)
        uc, cr_repo, _, _, _ = _build(cr, contract)

        saved = await uc.execute(cr.id)

        assert saved.status == ContractRequestStatus.ARCHIVED
        cr_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_signed_does_not_transition(self):
        """Depuis SIGNED, aucune transition (pas d'InvalidContractStatusError).

        Le statut reste SIGNED : appeler ``execute`` sans ``pytest.raises`` suffit
        à prouver qu'aucune exception de transition invalide n'est levée.
        """
        cr = ContractRequest(
            provisional_reference="PROV-2026-0002",
            status=ContractRequestStatus.SIGNED,
        )
        contract = _make_contract(cr)
        uc, cr_repo, _, _, _ = _build(cr, contract)

        saved = await uc.execute(cr.id)

        assert saved.status == ContractRequestStatus.SIGNED
        # Aucune entrée d'historique ne doit archiver la demande.
        assert all(entry["status"] != "archived" for entry in saved.status_history)
        cr_repo.save.assert_awaited_once()


class TestPurchaseOrderIdempotency:
    """Le BDC n'est créé qu'une fois : absent -> créé, déjà présent -> ignoré."""

    @pytest.mark.asyncio
    async def test_not_recreated_when_already_set(self):
        """``boond_purchase_order_id`` déjà défini -> create_purchase_order NON appelé."""
        cr = ContractRequest(
            provisional_reference="PROV-2026-0003",
            status=ContractRequestStatus.ACTIVE,
            third_party_id=uuid4(),
            daily_rate=Decimal("500"),
            boond_positioning_id=888,
        )
        contract = _make_contract(cr, boond_purchase_order_id=999)
        tp = MagicMock()
        tp.boond_provider_id = 12345
        uc, _, contract_repo, _, crm = _build(cr, contract, tp=tp)

        await uc.execute(cr.id)

        crm.create_purchase_order.assert_not_called()
        # Le provider existe déjà : pas de recréation non plus.
        crm.create_provider.assert_not_called()
        # La branche BDC (seul endroit qui sauve le contrat) n'est pas entrée.
        contract_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_created_when_absent(self):
        """``boond_purchase_order_id`` absent -> BDC créé une fois et persisté."""
        cr = ContractRequest(
            provisional_reference="PROV-2026-0004",
            status=ContractRequestStatus.ACTIVE,
            third_party_id=uuid4(),
            daily_rate=Decimal("450"),
            boond_positioning_id=777,
        )
        contract = _make_contract(cr)  # boond_purchase_order_id reste None
        tp = MagicMock()
        tp.boond_provider_id = 54321
        uc, _, contract_repo, _, crm = _build(cr, contract, tp=tp)
        crm.create_purchase_order = AsyncMock(return_value=42)

        await uc.execute(cr.id)

        crm.create_purchase_order.assert_awaited_once_with(
            provider_id=54321,
            positioning_id=777,
            reference=cr.display_reference,
            amount=450.0,
        )
        assert contract.boond_purchase_order_id == 42
        contract_repo.save.assert_awaited_once()
