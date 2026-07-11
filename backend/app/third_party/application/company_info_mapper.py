"""Shared mapping of company-info form data onto a ThirdParty entity.

Used by both the public portal (`POST /portal/{token}/company-info`, filled by the
tiers) and the internal ADV endpoint (`POST /contract-requests/{id}/third-party-info`,
filled by an ADV/admin who enters everything manually without soliciting the tiers).

Keeping the mapping here guarantees both entry points produce an identical
ThirdParty, so the generated draft is the same regardless of who typed the data.
"""

from app.third_party.domain.entities.third_party import ThirdParty


def compute_vat_number(siren: str) -> str | None:
    """Compute the French intracommunity VAT number from a SIREN.

    Returns None if the SIREN is not 9 digits.
    """
    if not siren or not siren.isdigit() or len(siren) != 9:
        return None
    siren_int = int(siren)
    key = (12 + 3 * (siren_int % 97)) % 97
    return f"FR{key:02d}{siren}"


def apply_company_info(tp: ThirdParty, body) -> None:
    """Apply a completed company-info form onto a ThirdParty (full submit).

    ``body`` must expose the ``CompanyInfoRequest`` fields: company identity plus
    representative and signatory / ADV / billing contacts (each with a
    ``*_same_as_representative`` boolean). Mutates ``tp`` in place and marks
    ``company_info_submitted = True``.
    """
    # Derive SIREN from first 9 digits of SIRET
    siren = body.siret[:9]

    # Auto-compute VAT number from SIREN if not provided
    vat_number = body.vat_number or compute_vat_number(siren)

    tp.entity_category = body.entity_category
    tp.company_info_submitted = True
    tp.company_name = body.company_name
    tp.legal_form = body.legal_form
    tp.capital = body.capital
    tp.siren = siren
    tp.siret = body.siret
    tp.vat_number = vat_number
    tp.ape_code = body.ape_code
    tp.rcs_city = body.rcs_city or body.head_office_city
    tp.rcs_number = siren  # In France, RCS registration number = SIREN
    tp.head_office_street = body.head_office_street
    tp.head_office_postal_code = body.head_office_postal_code
    tp.head_office_city = body.head_office_city
    tp.head_office_address = (
        f"{body.head_office_street}, {body.head_office_postal_code} {body.head_office_city}"
    )
    # Représentant légal
    tp.representative_civility = body.representative_civility
    tp.representative_first_name = body.representative_first_name
    tp.representative_last_name = body.representative_last_name
    tp.representative_email = body.representative_email
    tp.representative_phone = body.representative_phone
    tp.representative_title = body.representative_title
    tp.representative_name = f"{body.representative_first_name} {body.representative_last_name}"
    # Signataire
    if body.signatory_same_as_representative:
        tp.signatory_civility = body.representative_civility
        tp.signatory_first_name = body.representative_first_name
        tp.signatory_last_name = body.representative_last_name
        tp.signatory_email = body.representative_email
        tp.signatory_phone = body.representative_phone
    else:
        tp.signatory_civility = body.signatory_civility
        tp.signatory_first_name = body.signatory_first_name
        tp.signatory_last_name = body.signatory_last_name
        tp.signatory_email = body.signatory_email
        tp.signatory_phone = body.signatory_phone
    tp.signatory_is_director = body.signatory_is_director
    # Contact ADV
    if body.adv_contact_same_as_representative:
        tp.adv_contact_civility = body.representative_civility
        tp.adv_contact_first_name = body.representative_first_name
        tp.adv_contact_last_name = body.representative_last_name
        tp.adv_contact_email = body.representative_email
        tp.adv_contact_phone = body.representative_phone
    else:
        tp.adv_contact_civility = body.adv_contact_civility
        tp.adv_contact_first_name = body.adv_contact_first_name
        tp.adv_contact_last_name = body.adv_contact_last_name
        tp.adv_contact_email = body.adv_contact_email
        tp.adv_contact_phone = body.adv_contact_phone
    # Contact facturation
    if body.billing_contact_same_as_representative:
        tp.billing_contact_civility = body.representative_civility
        tp.billing_contact_first_name = body.representative_first_name
        tp.billing_contact_last_name = body.representative_last_name
        tp.billing_contact_email = body.representative_email
        tp.billing_contact_phone = body.representative_phone
    else:
        tp.billing_contact_civility = body.billing_contact_civility
        tp.billing_contact_first_name = body.billing_contact_first_name
        tp.billing_contact_last_name = body.billing_contact_last_name
        tp.billing_contact_email = body.billing_contact_email
        tp.billing_contact_phone = body.billing_contact_phone
