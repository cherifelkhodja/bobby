"""Shared SIRET → company-info lookup (INSEE Sirene + INPI RNE enrichment).

Extracted so both the public portal (magic-link authenticated) and the internal
ADV endpoint (JWT authenticated) can auto-fill company identity from a SIRET
without duplicating the INSEE/INPI plumbing.
"""

import httpx
import structlog
from fastapi import HTTPException, status

from app.third_party.api.schemas import SiretLookupResponse
from app.third_party.infrastructure.adapters.inpi_client import forme_juridique_label

logger = structlog.get_logger()


def _clean(val: str | None) -> str | None:
    """Return None if value is [ND] or empty."""
    if not val or val == "[ND]":
        return None
    return val


async def lookup_siret_data(siret: str, settings) -> SiretLookupResponse:
    """Look up company information from INSEE Sirene + INPI RNE for auto-fill.

    Raises HTTPException (4xx/5xx) on validation or upstream errors, so callers
    can propagate it directly.
    """
    if not settings.SIRENE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INSEE Sirene API non configurée.",
        )

    if len(siret) != 14 or not siret.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIRET invalide (14 chiffres requis).",
        )

    url = f"{settings.SIRENE_API_URL}/siret/{siret}"
    headers = {
        "X-INSEE-Api-Key-Integration": settings.SIRENE_API_KEY,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="L'API INSEE n'a pas répondu à temps.",
        )
    except Exception as exc:
        logger.error("sirene_lookup_error", error=str(exc), siret=siret)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors de la communication avec l'API INSEE.",
        )

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIRET introuvable dans la base INSEE.",
        )
    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Clé API INSEE invalide.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur INSEE ({resp.status_code}).",
        )

    data = resp.json()
    etab = data.get("etablissement", {})
    unite = etab.get("uniteLegale", {})
    adresse = etab.get("adresseEtablissement", {})

    siren = _clean(etab.get("siren"))
    company_name = _clean(unite.get("denominationUniteLegale"))
    categorie_code = _clean(unite.get("categorieJuridiqueUniteLegale")) or ""
    legal_form = forme_juridique_label(categorie_code) if categorie_code else None
    entity_category = "ei" if categorie_code.startswith("1") else "societe"

    # Build address
    parts = [
        _clean(adresse.get("numeroVoieEtablissement")),
        _clean(adresse.get("indiceRepetitionEtablissement")),
        _clean(adresse.get("typeVoieEtablissement")),
        _clean(adresse.get("libelleVoieEtablissement")),
    ]
    street = " ".join(p for p in parts if p) or None
    postal_code = _clean(adresse.get("codePostalEtablissement"))
    city = _clean(adresse.get("libelleCommuneEtablissement"))

    # Enrich with INPI RNE data (forme juridique, capital, greffe) — uses SIREN (first 9 digits)
    capital_str: str | None = None
    rcs_city: str | None = None
    inpi_configured = bool(settings.INPI_USERNAME and settings.INPI_PASSWORD) or bool(
        settings.INPI_TOKEN
    )
    if siren and inpi_configured:
        from app.third_party.infrastructure.adapters.inpi_client import InpiClient

        try:
            inpi = InpiClient(
                username=settings.INPI_USERNAME,
                password=settings.INPI_PASSWORD,
                token=settings.INPI_TOKEN,
            )
            inpi_info = await inpi.get_company(siren)
            if not inpi_info:
                logger.warning("inpi_no_data_returned", siren=siren)
            if inpi_info:
                # Forme juridique : INPI est source de vérité (RNE officiel)
                if inpi_info.legal_form_label:
                    legal_form = inpi_info.legal_form_label
                if inpi_info.capital_amount is not None:
                    capital_str = f"{inpi_info.capital_amount:,.0f}".replace(",", " ")
                rcs_city = inpi_info.greffe_city
        except Exception as exc:
            logger.warning(
                "inpi_enrich_failed", siren=siren, error=str(exc), error_type=type(exc).__name__
            )

    # APE/NAF code from INSEE
    ape_code = (
        _clean(etab.get("periodesEtablissement", [{}])[0].get("activitePrincipaleEtablissement"))
        if etab.get("periodesEtablissement")
        else None
    )
    if not ape_code:
        ape_code = _clean(unite.get("activitePrincipaleUniteLegale"))

    return SiretLookupResponse(
        siren=siren,
        company_name=company_name,
        legal_form=legal_form,
        entity_category=entity_category if categorie_code else None,
        head_office_street=street,
        head_office_postal_code=postal_code,
        head_office_city=city,
        capital=capital_str,
        rcs_city=rcs_city,
        ape_code=ape_code,
    )
