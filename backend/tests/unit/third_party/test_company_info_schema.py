"""Tests for the company-info request schemas (blank → None normalisation)."""

import pytest
from pydantic import ValidationError

from app.third_party.api.schemas import CompanyInfoDraftRequest, CompanyInfoRequest

VALID_PAYLOAD = {
    "entity_category": "societe",
    "company_name": "MVP TECHNOLOGY",
    "legal_form": "SAS",
    "capital": "1000",
    "siret": "95408912400018",
    "vat_number": "FR17954089124",
    "ape_code": "62.02A",
    "head_office_street": "229 RUE SAINT-HONORE",
    "head_office_postal_code": "75001",
    "head_office_city": "PARIS",
    "rcs_city": "Paris",
    "representative_civility": "M.",
    "representative_first_name": "Mohamed",
    "representative_last_name": "TALEB",
    "representative_email": "mohamed.taleb@mvp-technology.fr",
    "representative_phone": "",
    "representative_title": "Président",
    "signatory_same_as_representative": True,
    "signatory_civility": "M.",
    "signatory_first_name": "",
    "signatory_last_name": "",
    "signatory_email": "",
    "signatory_phone": "",
    "signatory_is_director": True,
    "adv_contact_same_as_representative": True,
    "adv_contact_civility": "M.",
    "adv_contact_first_name": "",
    "adv_contact_last_name": "",
    "adv_contact_email": "",
    "adv_contact_phone": "",
    "billing_contact_same_as_representative": True,
    "billing_contact_civility": "M.",
    "billing_contact_first_name": "",
    "billing_contact_last_name": "",
    "billing_contact_email": "",
    "billing_contact_phone": "",
}


def test_blank_optional_emails_become_none():
    """The ADV form posts "" for the contacts identical to the representative."""
    body = CompanyInfoRequest(**VALID_PAYLOAD)

    assert body.signatory_email is None
    assert body.adv_contact_email is None
    assert body.billing_contact_email is None
    assert body.representative_email == "mohamed.taleb@mvp-technology.fr"


def test_blank_optional_strings_become_none():
    body = CompanyInfoRequest(**VALID_PAYLOAD)

    assert body.representative_phone is None
    assert body.signatory_first_name is None
    assert body.signatory_phone is None


def test_blank_required_email_still_rejected():
    with pytest.raises(ValidationError) as exc:
        CompanyInfoRequest(**{**VALID_PAYLOAD, "representative_email": ""})

    assert "representative_email" in str(exc.value)


def test_malformed_optional_email_still_rejected():
    with pytest.raises(ValidationError) as exc:
        CompanyInfoRequest(**{**VALID_PAYLOAD, "signatory_email": "not-an-email"})

    assert "signatory_email" in str(exc.value)


def test_draft_request_accepts_blank_strings():
    draft = CompanyInfoDraftRequest(
        company_name="",
        siret="",
        representative_email="",
        signatory_email="",
        signatory_civility="",
        adv_contact_email="",
    )

    assert draft.company_name is None
    assert draft.representative_email is None
    assert draft.signatory_email is None
    assert draft.signatory_civility is None
