"""Tests for CreateSupplierDossierUseCase (ouverture d'un dossier fournisseur)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.create_supplier_dossier import (
    CreateSupplierDossierUseCase,
    SupplierDossierCommand,
    siren_from_siret,
)


def _make_use_case(existing_third_party=None):
    """Use case with fake repositories and a recording commercial validation."""
    saved: list = []

    cr_repo = AsyncMock()
    cr_repo.get_next_provisional_reference = AsyncMock(return_value="PROV-2026-007")
    cr_repo.save = AsyncMock(side_effect=lambda cr: (saved.append(cr), cr)[1])

    tp_repo = AsyncMock()
    tp_repo.get_by_siren = AsyncMock(return_value=existing_third_party)

    validate_commercial = AsyncMock()
    validate_commercial.execute = AsyncMock(side_effect=lambda command: command)

    use_case = CreateSupplierDossierUseCase(
        contract_request_repository=cr_repo,
        third_party_repository=tp_repo,
        validate_commercial_use_case=validate_commercial,
    )
    return use_case, saved, tp_repo, validate_commercial


def _command(**overrides) -> SupplierDossierCommand:
    defaults = {
        "third_party_type": "sous_traitant",
        "contact_email": "contact@fournisseur.fr",
        "commercial_email": "adv@geminiconsulting.fr",
    }
    defaults.update(overrides)
    return SupplierDossierCommand(**defaults)


class TestSirenExtraction:
    """Extraction du SIREN depuis un SIRET saisi à la main."""

    def test_takes_the_first_nine_digits(self):
        assert siren_from_siret("89421366900017") == "894213669"

    def test_ignores_separators(self):
        assert siren_from_siret("894 213 669 00017") == "894213669"

    def test_returns_none_when_too_short(self):
        assert siren_from_siret("8942") is None

    def test_returns_none_when_absent(self):
        assert siren_from_siret(None) is None
        assert siren_from_siret("") is None


class TestDossierCreation:
    """Création du dossier et rattachement du fournisseur."""

    @pytest.mark.asyncio
    async def test_creates_a_request_with_the_supplier_trigger(self):
        """Le dossier est tracé comme une ouverture manuelle fournisseur."""
        use_case, saved, _, _ = _make_use_case()

        await use_case.execute(_command())

        assert len(saved) == 1
        cr = saved[0]
        assert cr.trigger_type == "supplier_manual"
        assert cr.provisional_reference == "PROV-2026-007"
        assert cr.commercial_email == "adv@geminiconsulting.fr"
        # Aucun consultant : c'est tout l'objet de ce point d'entrée.
        assert cr.boond_candidate_id is None
        assert cr.boond_resource_id is None
        assert cr.boond_positioning_id is None

    @pytest.mark.asyncio
    async def test_reuses_the_existing_supplier_file_for_a_known_siret(self):
        """Un SIRET déjà connu rattache le dossier à la fiche existante."""
        existing = AsyncMock()
        existing.id = uuid4()
        use_case, saved, tp_repo, _ = _make_use_case(existing_third_party=existing)

        await use_case.execute(_command(siret="89421366900017"))

        tp_repo.get_by_siren.assert_awaited_once_with("894213669")
        assert saved[0].third_party_id == existing.id

    @pytest.mark.asyncio
    async def test_unknown_siret_leaves_the_supplier_to_be_created(self):
        """SIRET inconnu : la fiche sera créée par la validation commerciale."""
        use_case, saved, _, _ = _make_use_case(existing_third_party=None)

        await use_case.execute(_command(siret="89421366900017"))

        assert saved[0].third_party_id is None

    @pytest.mark.asyncio
    async def test_no_lookup_without_siret(self):
        """Sans SIRET, aucune recherche de doublon n'est tentée."""
        use_case, saved, tp_repo, _ = _make_use_case()

        await use_case.execute(_command())

        tp_repo.get_by_siren.assert_not_awaited()
        assert saved[0].third_party_id is None

    @pytest.mark.asyncio
    async def test_explicit_reuse_wins_over_the_siret_lookup(self):
        """Le rattachement choisi par l'ADV prime sur la recherche SIRET."""
        looked_up = AsyncMock()
        looked_up.id = uuid4()
        chosen_id = uuid4()
        use_case, saved, tp_repo, _ = _make_use_case(existing_third_party=looked_up)

        await use_case.execute(_command(siret="89421366900017", reuse_third_party_id=chosen_id))

        tp_repo.get_by_siren.assert_not_awaited()
        assert saved[0].third_party_id == chosen_id


class TestCommercialValidationHandoff:
    """Le dossier enchaîne directement sur la validation commerciale."""

    @pytest.mark.asyncio
    async def test_passes_type_contact_and_company(self):
        """Type de tiers, contact et société émettrice sont transmis."""
        company_id = uuid4()
        use_case, saved, _, validate_commercial = _make_use_case()

        command = await use_case.execute(
            _command(third_party_type="freelance", company_id=company_id)
        )

        validate_commercial.execute.assert_awaited_once()
        assert command.contract_request_id == saved[0].id
        assert command.third_party_type == "freelance"
        assert command.contact_email == "contact@fournisseur.fr"
        assert command.company_id == company_id

    @pytest.mark.asyncio
    async def test_portal_collection_is_the_default(self):
        """Par défaut le fournisseur reçoit le lien de collecte."""
        use_case, _, _, _ = _make_use_case()

        command = await use_case.execute(_command())

        assert command.notify_third_party is True
        assert command.skip_documents is False

    @pytest.mark.asyncio
    async def test_in_person_entry_is_propagated(self):
        """Le mode « saisie en personne » choisi à la création est transmis."""
        use_case, _, _, _ = _make_use_case()

        command = await use_case.execute(_command(notify_third_party=False, skip_documents=True))

        assert command.notify_third_party is False
        assert command.skip_documents is True

    @pytest.mark.asyncio
    async def test_sender_context_is_propagated(self):
        """Le contexte d'expédition de la société émettrice suit la commande."""
        use_case, _, _, _ = _make_use_case()

        command = await use_case.execute(
            _command(from_email="noreply@geminiconsulting.fr", company_name="Gemini")
        )

        assert command.from_email == "noreply@geminiconsulting.fr"
        assert command.company_name == "Gemini"
