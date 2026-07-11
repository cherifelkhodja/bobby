"""Tests for the shared company-info → ThirdParty mapper."""

from types import SimpleNamespace

from app.third_party.application.company_info_mapper import (
    apply_company_info,
    compute_vat_number,
)
from app.third_party.domain.entities.third_party import ThirdParty
from app.third_party.domain.value_objects.third_party_type import ThirdPartyType


def _body(**overrides) -> SimpleNamespace:
    """Build a CompanyInfoRequest-like object with sensible defaults."""
    defaults = {
        "entity_category": "societe",
        "company_name": "Acme SAS",
        "legal_form": "SAS",
        "capital": "10 000",
        "siret": "89421366900012",
        "vat_number": None,
        "ape_code": "6201Z",
        "head_office_street": "1 rue de la Paix",
        "head_office_postal_code": "75002",
        "head_office_city": "Paris",
        "rcs_city": None,
        "representative_civility": "M.",
        "representative_first_name": "Jean",
        "representative_last_name": "Dupont",
        "representative_email": "jean@acme.fr",
        "representative_phone": "+33612345678",
        "representative_title": "Président",
        "signatory_same_as_representative": False,
        "signatory_civility": "Mme",
        "signatory_first_name": "Marie",
        "signatory_last_name": "Martin",
        "signatory_email": "marie@acme.fr",
        "signatory_phone": None,
        "signatory_is_director": True,
        "adv_contact_same_as_representative": False,
        "adv_contact_civility": None,
        "adv_contact_first_name": None,
        "adv_contact_last_name": None,
        "adv_contact_email": None,
        "adv_contact_phone": None,
        "billing_contact_same_as_representative": False,
        "billing_contact_civility": None,
        "billing_contact_first_name": None,
        "billing_contact_last_name": None,
        "billing_contact_email": None,
        "billing_contact_phone": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _tp() -> ThirdParty:
    return ThirdParty(contact_email="contact@acme.fr", type=ThirdPartyType("sous_traitant"))


def test_compute_vat_number():
    # key = (12 + 3 * (894213669 % 97)) % 97 = (12 + 3*60) % 97 = 95
    assert compute_vat_number("894213669") == "FR95894213669"
    assert compute_vat_number("12345") is None
    assert compute_vat_number("abcdefghi") is None


def test_apply_company_info_derives_siren_vat_and_address():
    tp = _tp()
    apply_company_info(tp, _body())

    assert tp.company_info_submitted is True
    assert tp.company_name == "Acme SAS"
    assert tp.siren == "894213669"  # first 9 digits of SIRET
    assert tp.rcs_number == "894213669"  # RCS = SIREN in France
    assert tp.vat_number == "FR95894213669"  # auto-computed
    assert tp.head_office_address == "1 rue de la Paix, 75002 Paris"
    assert tp.representative_name == "Jean Dupont"
    # rcs_city falls back to head office city when not provided
    assert tp.rcs_city == "Paris"


def test_apply_company_info_distinct_signatory():
    tp = _tp()
    apply_company_info(tp, _body())

    assert tp.signatory_first_name == "Marie"
    assert tp.signatory_last_name == "Martin"
    assert tp.signatory_is_director is True


def test_apply_company_info_signatory_same_as_representative():
    tp = _tp()
    apply_company_info(tp, _body(signatory_same_as_representative=True))

    assert tp.signatory_first_name == "Jean"
    assert tp.signatory_last_name == "Dupont"
    assert tp.signatory_email == "jean@acme.fr"


def test_apply_company_info_explicit_vat_preserved():
    tp = _tp()
    apply_company_info(tp, _body(vat_number="FR99894213669"))

    assert tp.vat_number == "FR99894213669"
