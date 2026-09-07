"""Rattacher un fournisseur à une société déjà présente dans BoondManager.

Deux règles vivent dans ``boond_supplier`` : l'immatriculation Boond se
compare au SIRET du tiers sur les chiffres, et la recherche d'un contact
existant ne bloque jamais le report quand elle échoue.
"""

from unittest.mock import AsyncMock

import pytest

from app.contract_management.application.boond_contacts import SupplierContact
from app.contract_management.application.boond_supplier import (
    find_existing_contact_id,
    registration_matches,
)


class TestRegistrationMatches:
    """Le SIRET du tiers contre le ``registrationNumber`` de Boond."""

    def test_same_siret_with_spaces(self):
        assert registration_matches("894 213 669 00012", "89421366900012") is True

    def test_different_siret(self):
        assert registration_matches("89421366900012", "89421366900020") is False

    def test_siren_only_compares_to_siren_part(self):
        assert registration_matches("894 213 669", "89421366900012") is True
        assert registration_matches("894213670", "89421366900012") is False

    def test_no_verdict_when_either_side_is_missing(self):
        assert registration_matches(None, "89421366900012") is None
        assert registration_matches("", "89421366900012") is None
        assert registration_matches("894213669", None) is None
        assert registration_matches("R.C.S.", "89421366900012") is None


def _contact(email: str | None) -> SupplierContact:
    return SupplierContact(
        roles=("adv",),
        civility="M.",
        first_name="Jean",
        last_name="Dupont",
        email=email,
        phone=None,
        job_title="ADV",
        types_of=(9,),
    )


class TestFindExistingContactId:
    """La recherche par e-mail est un bonus : sans adresse ou en panne, rien."""

    @pytest.mark.asyncio
    async def test_returns_the_contact_found(self):
        crm = AsyncMock()
        crm.find_contact_by_email = AsyncMock(return_value=42)

        assert await find_existing_contact_id(crm, 123, _contact("jean@acme.test")) == 42
        crm.find_contact_by_email.assert_awaited_once_with(123, "jean@acme.test")

    @pytest.mark.asyncio
    async def test_no_lookup_without_email(self):
        crm = AsyncMock()
        crm.find_contact_by_email = AsyncMock(return_value=42)

        assert await find_existing_contact_id(crm, 123, _contact(None)) is None
        crm.find_contact_by_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_failure_means_no_match_not_an_error(self):
        crm = AsyncMock()
        crm.find_contact_by_email = AsyncMock(side_effect=RuntimeError("boond down"))

        assert await find_existing_contact_id(crm, 123, _contact("jean@acme.test")) is None
