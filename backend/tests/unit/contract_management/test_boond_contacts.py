"""Contacts fournisseur poussés dans BoondManager.

Les `typesOf` viennent de la configuration du CRM du groupe (Administration →
Types des contacts) : 2 = Contact facturation, 7 = Dirigeant, 8 = Commercial,
9 = Contact ADV, 10 = Signataire. Ces tests les verrouillent, une erreur de
type rangeant le contact dans la mauvaise colonne du CRM sans rien casser.
"""

from types import SimpleNamespace

from app.contract_management.application.boond_contacts import (
    CONTACT_TYPE_ADV,
    CONTACT_TYPE_DIRIGEANT,
    CONTACT_TYPE_FACTURATION,
    CONTACT_TYPE_SIGNATAIRE,
    split_supplier_contacts,
    supplier_contacts,
)


def _third_party(**overrides) -> SimpleNamespace:
    defaults = {
        "representative_civility": "M.",
        "representative_first_name": "Karim",
        "representative_last_name": "BENALI",
        "representative_email": "karim@akema-tech.fr",
        "representative_phone": "0601020304",
        "representative_title": "Président",
        "signatory_civility": None,
        "signatory_first_name": None,
        "signatory_last_name": None,
        "signatory_email": None,
        "signatory_phone": None,
        "signatory_is_director": False,
        "adv_contact_civility": "Mme",
        "adv_contact_first_name": "Nadia",
        "adv_contact_last_name": "SELLAM",
        "adv_contact_email": "adv@akema-tech.fr",
        "adv_contact_phone": "0601020305",
        "billing_contact_civility": "Mme",
        "billing_contact_first_name": "Claire",
        "billing_contact_last_name": "MOREAU",
        "billing_contact_email": "compta@akema-tech.fr",
        "billing_contact_phone": "0601020306",
        # Aucun contact encore reporté dans Boond.
        "boond_signatory_contact_id": None,
        "boond_adv_contact_id": None,
        "boond_billing_contact_id": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestRoles:
    """Chaque rôle Bobby prend son type dans le CRM."""

    def test_three_distinct_people_give_three_contacts(self):
        contacts = supplier_contacts(_third_party())

        assert [c.roles for c in contacts] == [("signataire",), ("adv",), ("facturation",)]
        assert [c.types_of for c in contacts] == [
            (CONTACT_TYPE_SIGNATAIRE,),
            (CONTACT_TYPE_ADV,),
            (CONTACT_TYPE_FACTURATION,),
        ]

    def test_the_billing_contact_is_not_a_commercial(self):
        """Le contact facturation prend le type 2, pas « Commercial » (8)."""
        contacts = supplier_contacts(_third_party())
        billing = next(c for c in contacts if "facturation" in c.roles)

        assert billing.types_of == (CONTACT_TYPE_FACTURATION,)
        assert billing.job_title == "Facturation"
        assert billing.email == "compta@akema-tech.fr"

    def test_a_director_signatory_carries_both_types(self):
        contacts = supplier_contacts(_third_party(signatory_is_director=True))
        signatory = contacts[0]

        assert signatory.types_of == (CONTACT_TYPE_SIGNATAIRE, CONTACT_TYPE_DIRIGEANT)

    def test_the_legal_representative_signs_when_no_signatory_is_given(self):
        """Comme dans les documents, le représentant légal signe à défaut."""
        signatory = supplier_contacts(_third_party())[0]

        assert signatory.first_name == "Karim"
        assert signatory.email == "karim@akema-tech.fr"
        assert signatory.job_title == "Président"

    def test_an_explicit_signatory_wins_over_the_representative(self):
        contacts = supplier_contacts(
            _third_party(
                signatory_civility="Mme",
                signatory_first_name="Sonia",
                signatory_last_name="HADDAD",
                signatory_email="sonia@akema-tech.fr",
            )
        )

        assert contacts[0].first_name == "Sonia"
        assert contacts[0].email == "sonia@akema-tech.fr"


class TestDeduplication:
    """Une personne qui cumule les rôles ne fait qu'un contact."""

    def test_the_same_person_in_three_roles_gives_one_contact(self):
        """Cas courant chez un freelance : le gérant est tout à la fois."""
        solo = _third_party(
            adv_contact_civility="M.",
            adv_contact_first_name="Karim",
            adv_contact_last_name="BENALI",
            adv_contact_email="karim@akema-tech.fr",
            billing_contact_civility="M.",
            billing_contact_first_name="Karim",
            billing_contact_last_name="BENALI",
            billing_contact_email="karim@akema-tech.fr",
        )

        contacts = supplier_contacts(solo)

        assert len(contacts) == 1
        assert contacts[0].roles == ("signataire", "adv", "facturation")
        assert contacts[0].types_of == (
            CONTACT_TYPE_SIGNATAIRE,
            CONTACT_TYPE_ADV,
            CONTACT_TYPE_FACTURATION,
        )
        # La vraie fonction survit aux libellés de repli des autres rôles.
        assert contacts[0].job_title == "Président"

    def test_the_identity_match_ignores_case_and_spacing(self):
        contacts = supplier_contacts(
            _third_party(
                adv_contact_first_name=" karim ",
                adv_contact_last_name="benali",
                adv_contact_email="KARIM@akema-tech.fr",
            )
        )

        assert len(contacts) == 2
        assert contacts[0].roles == ("signataire", "adv")

    def test_a_role_without_identity_is_skipped(self):
        """Boond créerait une fiche vide : mieux vaut ne rien envoyer."""
        contacts = supplier_contacts(
            _third_party(
                billing_contact_first_name=None,
                billing_contact_last_name=None,
                billing_contact_email=None,
            )
        )

        assert [c.roles for c in contacts] == [("signataire",), ("adv",)]


class TestAlreadyPushed:
    """Un contact déjà reporté n'est pas recréé.

    Le report manuel avant signature et la synchronisation à la signature
    passent tous deux ici : sans cette garde, le second laisserait des doublons
    dans le CRM.
    """

    def test_nothing_is_pushed_yet(self):
        to_create, already_pushed = split_supplier_contacts(_third_party())

        assert len(to_create) == 3
        assert already_pushed == []

    def test_a_pushed_contact_is_not_recreated(self):
        to_create, already_pushed = split_supplier_contacts(
            _third_party(boond_signatory_contact_id=4242)
        )

        assert [c.roles for c in already_pushed] == [("signataire",)]
        assert [c.roles for c in to_create] == [("adv",), ("facturation",)]

    def test_a_fully_pushed_supplier_has_nothing_left_to_create(self):
        to_create, already_pushed = split_supplier_contacts(
            _third_party(
                boond_signatory_contact_id=4242,
                boond_adv_contact_id=4243,
                boond_billing_contact_id=4244,
            )
        )

        assert to_create == []
        assert len(already_pushed) == 3

    def test_a_contact_gaining_a_role_is_recreated(self):
        """Boond ne sait pas compléter les types d'un contact existant."""
        solo = _third_party(
            adv_contact_first_name="Karim",
            adv_contact_last_name="BENALI",
            adv_contact_email="karim@akema-tech.fr",
            boond_signatory_contact_id=4242,
        )

        to_create, already_pushed = split_supplier_contacts(solo)

        # La personne cumule signataire et ADV ; seul le rôle de signataire est
        # reporté, donc le contact repart pour porter les deux types.
        assert already_pushed == []
        assert [c.roles for c in to_create] == [("signataire", "adv"), ("facturation",)]
