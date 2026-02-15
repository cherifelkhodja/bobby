"""INSEE/Sirene API client for SIREN verification.

Uses OAuth2 client_credentials flow to obtain and cache Bearer tokens.
"""

import time
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

INSEE_SIRENE_BASE_URL = "https://api.insee.fr/entreprises/sirene/V3.11"
INSEE_TOKEN_URL = "https://auth.insee.net/auth/realms/apim-gravitee/protocol/openid-connect/token"


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

    Uses OAuth2 client_credentials flow with automatic token refresh.
    """

    def __init__(self, consumer_key: str, consumer_secret: str) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def _get_access_token(self) -> str | None:
        """Obtain or return cached OAuth2 access token."""
        # Return cached token if still valid (with 60s margin)
        if self._access_token and time.monotonic() < self._token_expires_at - 60:
            return self._access_token

        if not self._consumer_key or not self._consumer_secret:
            logger.warning("insee_credentials_not_configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    INSEE_TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._consumer_key,
                        "client_secret": self._consumer_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                token_data = response.json()

            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.monotonic() + expires_in

            logger.info("insee_token_obtained", expires_in=expires_in)
            return self._access_token

        except httpx.HTTPStatusError as exc:
            logger.error(
                "insee_token_request_failed",
                status_code=exc.response.status_code,
                body=exc.response.text[:200],
            )
            return None
        except httpx.RequestError as exc:
            logger.error("insee_token_request_error", error=str(exc))
            return None

    async def verify_siren(self, siren: str) -> InseeCompanyInfo | None:
        """Verify a SIREN number and fetch company information.

        Args:
            siren: The 9-digit SIREN number to verify.

        Returns:
            Company information if found, None otherwise.
        """
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{INSEE_SIRENE_BASE_URL}/siren/{siren}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info("insee_siren_not_found", siren=siren)
                return None

            if response.status_code == 401:
                # Token expired unexpectedly, clear cache and retry once
                self._access_token = None
                self._token_expires_at = 0
                token = await self._get_access_token()
                if not token:
                    return None
                headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.error("insee_authentication_failed_after_retry")
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
