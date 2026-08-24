"""Contacts fournisseur poussés dans BoondManager.

Les `typesOf` sont **configurés dans BoondManager** (Administration → Types des
contacts) ; les constantes ci-dessous reprennent la configuration du CRM du
groupe. Les changer côté CRM impose de les changer ici.

Bobby collecte trois rôles auprès du fournisseur — signataire, contact ADV,
contact facturation — mais une même personne les cumule souvent. Boond veut
alors **un seul contact portant plusieurs types**, pas trois fiches homonymes :
c'est tout l'objet du dédoublonnage ci-dessous, partagé par la synchronisation
automatique et par l'action manuelle de l'ADV.
"""

from dataclasses import dataclass

CONTACT_TYPE_DECIDEUR = 0
CONTACT_TYPE_PRESCRIPTEUR = 1
CONTACT_TYPE_FACTURATION = 2
CONTACT_TYPE_ACHETEUR = 3
CONTACT_TYPE_INACTIF = 5
CONTACT_TYPE_DIRIGEANT = 7
CONTACT_TYPE_COMMERCIAL = 8
CONTACT_TYPE_ADV = 9
CONTACT_TYPE_SIGNATAIRE = 10

# Fonctions de repli, posées faute de titre saisi : elles ne doivent jamais
# chasser la vraie fonction d'une personne qui cumule les rôles.
GENERIC_JOB_TITLES = frozenset({"ADV", "Facturation"})


@dataclass(frozen=True)
class SupplierContact:
    """Un contact à créer dans Boond, avec les rôles Bobby qu'il porte."""

    roles: tuple[str, ...]
    civility: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    job_title: str | None
    types_of: tuple[int, ...]


def _identity_key(first_name: str | None, last_name: str | None, email: str | None) -> str:
    """Clé d'identité d'un contact : deux rôles tenus par la même personne fusionnent."""
    return "|".join((part or "").strip().lower() for part in (first_name, last_name, email))


def supplier_contacts(third_party) -> list[SupplierContact]:
    """Contacts Boond à créer pour un fournisseur, dédoublonnés par identité.

    L'ordre suit celui des rôles : signataire, ADV, facturation. Un rôle dont
    ni le prénom ni l'adresse ne sont connus est ignoré — Boond créerait une
    fiche vide. À défaut de signataire saisi, c'est le représentant légal qui
    signe, comme dans les documents.
    """
    signatory_types = [CONTACT_TYPE_SIGNATAIRE]
    if third_party.signatory_is_director:
        signatory_types.append(CONTACT_TYPE_DIRIGEANT)

    roles = [
        (
            "signataire",
            third_party.signatory_civility or third_party.representative_civility,
            third_party.signatory_first_name or third_party.representative_first_name,
            third_party.signatory_last_name or third_party.representative_last_name,
            third_party.signatory_email or third_party.representative_email,
            third_party.signatory_phone or third_party.representative_phone,
            third_party.representative_title,
            signatory_types,
        ),
        (
            "adv",
            third_party.adv_contact_civility,
            third_party.adv_contact_first_name,
            third_party.adv_contact_last_name,
            third_party.adv_contact_email,
            third_party.adv_contact_phone,
            "ADV",
            [CONTACT_TYPE_ADV],
        ),
        (
            "facturation",
            third_party.billing_contact_civility,
            third_party.billing_contact_first_name,
            third_party.billing_contact_last_name,
            third_party.billing_contact_email,
            third_party.billing_contact_phone,
            "Facturation",
            [CONTACT_TYPE_FACTURATION],
        ),
    ]

    merged: dict[str, dict] = {}
    for role, civility, first_name, last_name, email, phone, job_title, types_of in roles:
        if not (first_name or email):
            continue
        key = _identity_key(first_name, last_name, email)
        existing = merged.get(key)
        if existing is None:
            merged[key] = {
                "roles": [role],
                "civility": civility,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "job_title": job_title,
                "types_of": list(types_of),
            }
            continue
        existing["roles"].append(role)
        for type_of in types_of:
            if type_of not in existing["types_of"]:
                existing["types_of"].append(type_of)
        if job_title and job_title not in GENERIC_JOB_TITLES:
            existing["job_title"] = job_title

    return [
        SupplierContact(
            roles=tuple(entry["roles"]),
            civility=entry["civility"],
            first_name=entry["first_name"],
            last_name=entry["last_name"],
            email=entry["email"],
            phone=entry["phone"],
            job_title=entry["job_title"],
            types_of=tuple(entry["types_of"]),
        )
        for entry in merged.values()
    ]


# Identifiant Boond déjà enregistré, par rôle : c'est lui qui dit si un contact
# a déjà été reporté.
ROLE_CONTACT_ID_FIELDS = {
    "signataire": "boond_signatory_contact_id",
    "adv": "boond_adv_contact_id",
    "facturation": "boond_billing_contact_id",
}


def persisted_contact_ids(third_party) -> dict[str, int | None]:
    """Identifiants Boond des contacts déjà reportés, par rôle."""
    return {
        role: getattr(third_party, field, None) for role, field in ROLE_CONTACT_ID_FIELDS.items()
    }


def split_supplier_contacts(third_party) -> tuple[list[SupplierContact], list[SupplierContact]]:
    """Sépare les contacts à créer de ceux déjà reportés dans BoondManager.

    Un contact dont **tous** les rôles portent déjà un identifiant Boond n'est
    pas recréé : sans cette garde, le report manuel avant signature puis la
    synchronisation à la signature laisseraient des doublons dans le CRM. Un
    contact qui gagne un rôle depuis le dernier report est en revanche recréé,
    faute de pouvoir compléter ses types autrement.
    """
    ids = persisted_contact_ids(third_party)
    to_create: list[SupplierContact] = []
    already_pushed: list[SupplierContact] = []
    for contact in supplier_contacts(third_party):
        if all(ids.get(role) for role in contact.roles):
            already_pushed.append(contact)
        else:
            to_create.append(contact)
    return to_create, already_pushed
