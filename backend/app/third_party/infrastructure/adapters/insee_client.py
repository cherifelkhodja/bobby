"""INSEE/Sirene API client for SIREN verification."""

from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

INSEE_SIRENE_BASE_URL = "https://api.insee.fr/entreprises/sirene/V3.11"


@dataclass
class InseeCompanyInfo:
    """Company information from INSEE/Sirene API."""

    siren: str
    siret: str
    company_name: str
    legal_form: str
    head_office_address: str
    is_active: bool


class InseeClient:
    """Client for INSEE/Sirene API to verify SIREN numbers.

    Uses the API Sirene V3.11 to look up company information.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def verify_siren(self, siren: str) -> InseeCompanyInfo | None:
        """Verify a SIREN number and fetch company information.

        Args:
            siren: The 9-digit SIREN number to verify.

        Returns:
            Company information if found, None otherwise.
        """
        if not self._api_key:
            logger.warning("insee_api_key_not_configured")
            return None

        url = f"{INSEE_SIRENE_BASE_URL}/siren/{siren}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info("insee_siren_not_found", siren=siren)
                return None

            if response.status_code == 401:
                logger.error("insee_authentication_failed")
                return None

            response.raise_for_status()
            data = response.json()

            unite = data.get("uniteLegale", {})
            periodes = unite.get("periodesUniteLegale", [{}])
            derniere_periode = periodes[0] if periodes else {}

            # Build company name
            denomination = derniere_periode.get("denominationUniteLegale", "")
            if not denomination:
                prenom = unite.get("prenom1UniteLegale", "")
                nom = derniere_periode.get("nomUsageUniteLegale", "")
                denomination = f"{prenom} {nom}".strip()

            # Legal form code
            legal_form_code = derniere_periode.get("categorieJuridiqueUniteLegale", "")

            # Activity status
            etat_admin = derniere_periode.get("etatAdministratifUniteLegale", "")
            is_active = etat_admin == "A"

            # Get head office SIRET
            siret_siege = unite.get("nicSiegeUniteLegale", "")
            siret = f"{siren}{siret_siege}" if siret_siege else siren

            logger.info(
                "insee_siren_verified",
                siren=siren,
                company_name=denomination,
                is_active=is_active,
            )

            return InseeCompanyInfo(
                siren=siren,
                siret=siret,
                company_name=denomination,
                legal_form=legal_form_code,
                head_office_address="",
                is_active=is_active,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "insee_api_error",
                siren=siren,
                status_code=exc.response.status_code,
            )
            return None
        except httpx.RequestError as exc:
            logger.error(
                "insee_api_request_error",
                siren=siren,
                error=str(exc),
            )
            return None
