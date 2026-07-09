"""Tests for ConfigureContractUseCase.

Verrouille deux correctifs :
- la fusion préserve les clés d'édition par contrat (`article_overrides`,
  `custom_articles`, `article_order`, `deleted_article_keys`, ...) gérées par
  l'endpoint article-overrides, qu'un `configure` écraserait sinon ;
- `company_id` n'est touché que si la clé est présente dans le payload ; absente,
  la société déjà résolue n'est PAS effacée.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contract_management.application.use_cases.configure_contract import (
    ConfigureContractUseCase,
)
from app.contract_management.domain.entities.contract_request import ContractRequest
from app.contract_management.domain.exceptions import ContractRequestNotFoundError
from app.contract_management.domain.value_objects.contract_request_status import (
    ContractRequestStatus,
)


def _make_cr(**overrides) -> ContractRequest:
    """Create a test ContractRequest entity."""
    defaults = {
        "provisional_reference": "PROV-2026-0001",
        "trigger_type": "candidat_11",
        "status": ContractRequestStatus.REVIEWING_COMPLIANCE,
    }
    defaults.update(overrides)
    return ContractRequest(**defaults)


def _make_use_case(cr: ContractRequest) -> ConfigureContractUseCase:
    """Create use case with a mock repo pre-loaded with the CR."""
    cr_repo = AsyncMock()
    cr_repo.get_by_id = AsyncMock(return_value=cr)
    cr_repo.save = AsyncMock(side_effect=lambda x: x)
    return ConfigureContractUseCase(contract_request_repository=cr_repo)


class TestEditionKeysPreserved:
    """The merge must not wipe per-contract edition keys."""

    @pytest.mark.asyncio
    async def test_reinjects_all_edition_keys(self):
        """Existing article/annex customisations survive a new configure call."""
        old_config = {
            "article_overrides": {"article_1": "Texte personnalisé"},
            "annex_overrides": {"annex_1": "Annexe personnalisée"},
            "custom_articles": [{"key": "custom_1", "title": "Clause spéciale"}],
            "custom_annexes": [{"key": "annex_custom_1"}],
            "article_order": ["article_1", "article_2"],
            "annex_order": ["annex_1", "annex_2"],
            "deleted_article_keys": ["article_9"],
            "deleted_annex_keys": ["annex_9"],
            "payment_terms": "30 jours ANCIEN",  # non-edition -> remplaçable
            "stale_setting": "doit disparaître",  # non-edition, absent du nouveau
        }
        cr = _make_cr(contract_config=old_config)
        uc = _make_use_case(cr)

        new_config = {"payment_terms": "45 jours NOUVEAU", "penalty_rate": "10%"}
        result = await uc.execute(cr.id, new_config)

        cfg = result.contract_config
        # Toutes les clés d'édition réinjectées avec les anciennes valeurs
        assert cfg["article_overrides"] == {"article_1": "Texte personnalisé"}
        assert cfg["annex_overrides"] == {"annex_1": "Annexe personnalisée"}
        assert cfg["custom_articles"] == [{"key": "custom_1", "title": "Clause spéciale"}]
        assert cfg["custom_annexes"] == [{"key": "annex_custom_1"}]
        assert cfg["article_order"] == ["article_1", "article_2"]
        assert cfg["annex_order"] == ["annex_1", "annex_2"]
        assert cfg["deleted_article_keys"] == ["article_9"]
        assert cfg["deleted_annex_keys"] == ["annex_9"]

        # Le nouveau config est appliqué pour les clés non-édition
        assert cfg["payment_terms"] == "45 jours NOUVEAU"
        assert cfg["penalty_rate"] == "10%"

        # Une clé non-édition absente du nouveau payload est bien remplacée (droppée)
        assert "stale_setting" not in cfg

    @pytest.mark.asyncio
    async def test_no_previous_config_keeps_new_config_as_is(self):
        """Without previous config, the new config is stored unchanged."""
        cr = _make_cr(contract_config=None)
        uc = _make_use_case(cr)

        new_config = {"payment_terms": "60 jours", "article_overrides": {"a": "b"}}
        result = await uc.execute(cr.id, new_config)

        assert result.contract_config == new_config
        uc._cr_repo.save.assert_awaited_once()


class TestCompanyIdHandling:
    """company_id is only touched when the key is present in the payload."""

    @pytest.mark.asyncio
    async def test_company_id_present_is_updated(self):
        """A company_id in the payload updates the CR (parsed to UUID)."""
        old_company = uuid4()
        new_company = uuid4()
        cr = _make_cr(company_id=old_company)
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, {"company_id": str(new_company), "payment_terms": "30"})

        assert result.company_id == new_company

    @pytest.mark.asyncio
    async def test_company_id_absent_is_preserved(self):
        """An absent company_id key must NOT wipe an already-resolved company."""
        existing_company = uuid4()
        cr = _make_cr(company_id=existing_company)
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, {"payment_terms": "30"})

        # Non écrasé : la société auto-résolue est conservée
        assert result.company_id == existing_company

    @pytest.mark.asyncio
    async def test_company_id_present_but_empty_clears(self):
        """A present-but-falsy company_id explicitly clears the company."""
        cr = _make_cr(company_id=uuid4())
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, {"company_id": None, "payment_terms": "30"})

        assert result.company_id is None

    @pytest.mark.asyncio
    async def test_company_id_malformed_falls_back_to_none(self):
        """A malformed company_id string is swallowed and set to None."""
        cr = _make_cr(company_id=uuid4())
        uc = _make_use_case(cr)

        result = await uc.execute(cr.id, {"company_id": "pas-un-uuid", "payment_terms": "30"})

        assert result.company_id is None


class TestNotFound:
    """Missing contract request raises the domain error."""

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self):
        """Unknown ID raises ContractRequestNotFoundError and never saves."""
        cr_repo = AsyncMock()
        cr_repo.get_by_id = AsyncMock(return_value=None)
        cr_repo.save = AsyncMock()
        uc = ConfigureContractUseCase(contract_request_repository=cr_repo)

        with pytest.raises(ContractRequestNotFoundError):
            await uc.execute(uuid4(), {"payment_terms": "30"})

        cr_repo.save.assert_not_called()
