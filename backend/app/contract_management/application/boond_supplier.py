"""Report d'un fournisseur dans BoondManager : société et contacts.

Deux chemins mènent au CRM — l'action manuelle de l'ADV avant signature, et
la synchronisation à la signature — et ils doivent y laisser la même chose :
une société, ses contacts, sans doublon. Ce module porte ce qu'ils partagent
quand la société **existe déjà** dans Boond : la comparaison de son
immatriculation au SIRET du tiers, et la réutilisation d'un contact que le
CRM connaît déjà.
"""

import re

import structlog

logger = structlog.get_logger()


def registration_matches(registration_number: str | None, siret: str | None) -> bool | None:
    """L'immatriculation d'une société Boond est-elle celle du tiers ?

    Boond range SIREN et NIC dans ``registrationNumber``, avec ou sans
    espaces, parfois le SIREN seul. La comparaison porte sur les chiffres :
    un SIREN seul se compare aux neuf premiers chiffres du SIRET. ``None``
    quand l'un des deux manque — rien à comparer, donc pas de verdict.
    """
    boond_digits = re.sub(r"\D", "", registration_number or "")
    siret_digits = re.sub(r"\D", "", siret or "")
    if not boond_digits or not siret_digits:
        return None
    if len(boond_digits) == 9:
        return boond_digits == siret_digits[:9]
    return boond_digits == siret_digits


async def find_existing_contact_id(crm, company_id: int, contact) -> int | None:
    """Identifiant Boond d'un contact que la société connaît déjà, par e-mail.

    Un échec de la recherche ne bloque pas le report : le contact est alors
    créé, quitte à laisser un doublon que l'ADV verra. L'inverse — un report
    qui s'arrête sur une recherche en panne — coûterait plus.
    """
    if not contact.email:
        return None
    try:
        return await crm.find_contact_by_email(company_id, contact.email)
    except Exception as exc:
        logger.warning(
            "boond_find_contact_failed",
            company_id=company_id,
            email=contact.email,
            error=str(exc),
        )
        return None
