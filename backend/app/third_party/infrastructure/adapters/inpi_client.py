"""INPI RNE API client for company information lookup.

Uses username/password → Bearer token flow (token cached until expiry).
Fetches forme juridique, capital social, and ville du greffe for a given SIREN.
"""

import time
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()

INPI_BASE_URL = "https://registre-national-entreprises.inpi.fr/api"
INPI_LOGIN_URL = f"{INPI_BASE_URL}/sso/login"
INPI_TOKEN_TTL_SECONDS = 3600  # Tokens are short-lived; refresh every hour


@dataclass
class InpiCompanyInfo:
    """Company information fetched from INPI RNE."""

    siren: str
    company_name: str
    legal_form: str | None
    capital_amount: float | None
    capital_currency: str | None
    greffe_city: str | None


class InpiClient:
    """Client for the INPI Registre National des Entreprises (RNE) API.

    Authentication: POST /api/sso/login with username/password → Bearer token.
    Token is cached and refreshed before expiry.
    """

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def _get_access_token(self) -> str | None:
        """Obtain or return cached Bearer token."""
        # Refresh 60s before expiry
        if self._access_token and time.monotonic() < self._token_expires_at - 60:
            return self._access_token

        if not self._username or not self._password:
            logger.warning("inpi_credentials_not_configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    INPI_LOGIN_URL,
                    json={"username": self._username, "password": self._password},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

            token = data.get("token")
            if not token:
                logger.error("inpi_login_no_token", response=str(data)[:200])
                return None

            self._access_token = token
            self._token_expires_at = time.monotonic() + INPI_TOKEN_TTL_SECONDS
            logger.info("inpi_token_obtained")
            return self._access_token

        except httpx.HTTPStatusError as exc:
            logger.error(
                "inpi_login_failed",
                status_code=exc.response.status_code,
                body=exc.response.text[:200],
            )
            return None
        except httpx.RequestError as exc:
            logger.error("inpi_login_request_error", error=str(exc))
            return None

    async def get_company(self, siren: str) -> InpiCompanyInfo | None:
        """Fetch company info from INPI RNE by SIREN.

        Returns InpiCompanyInfo with legal form, capital, and greffe city,
        or None if not found or on error.
        """
        token = await self._get_access_token()
        if not token:
            return None

        url = f"{INPI_BASE_URL}/companies/{siren}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info("inpi_company_not_found", siren=siren)
                return None

            if response.status_code == 401:
                # Token rejected — clear and retry once
                self._access_token = None
                self._token_expires_at = 0
                token = await self._get_access_token()
                if not token:
                    return None
                headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.error("inpi_auth_failed_after_retry", siren=siren)
                    return None

            response.raise_for_status()
            data = response.json()

            return self._parse_company(siren, data)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "inpi_api_error",
                siren=siren,
                status_code=exc.response.status_code,
            )
            return None
        except httpx.RequestError as exc:
            logger.error("inpi_api_request_error", siren=siren, error=str(exc))
            return None

    def _parse_company(self, siren: str, data: dict) -> InpiCompanyInfo:
        """Extract relevant fields from INPI RNE JSON response.

        The INPI response wraps data under formality.content with either
        'personneMorale' or 'personnePhysique' depending on the entity type.
        """
        formality = data.get("formality", data)  # Top-level may already be the formality
        content = formality.get("content", {})

        # Entity can be a legal person (société) or natural person (auto-entrepreneur)
        entity = content.get("personneMorale") or content.get("personnePhysique") or {}
        identity = entity.get("identite", {})
        entreprise = identity.get("entrepreneur", {}).get("entreprise", {})
        description = identity.get("entrepreneur", {}).get("description", {})

        # Company name
        company_name = (
            entreprise.get("denominationSociale")
            or identity.get("denominationSociale")
            or formality.get("siren", siren)
        )

        # Legal form — may be an object {"code": "...", "libelle": "..."} or a string
        forme_raw = entreprise.get("formeJuridique") or identity.get("formeJuridique")
        if isinstance(forme_raw, dict):
            legal_form = forme_raw.get("libelle") or forme_raw.get("code")
        elif isinstance(forme_raw, str):
            legal_form = forme_raw or None
        else:
            legal_form = None

        # Capital social
        capital_raw = entreprise.get("capital") or identity.get("capital") or {}
        if isinstance(capital_raw, dict):
            capital_amount = capital_raw.get("montantCapital")
            capital_currency = capital_raw.get("deviseCapital", "EUR")
        else:
            capital_amount = None
            capital_currency = None

        # Ville du greffe
        lieu = (
            description.get("lieuImmatriculation", {})
            or identity.get("lieuImmatriculation", {})
        )
        greffe_raw = lieu.get("greffe")
        if isinstance(greffe_raw, dict):
            greffe_city = greffe_raw.get("denomination") or greffe_raw.get("libelle")
        elif isinstance(greffe_raw, str):
            greffe_city = greffe_raw or None
        else:
            greffe_city = None

        logger.info(
            "inpi_company_parsed",
            siren=siren,
            company_name=company_name,
            legal_form=legal_form,
            capital_amount=capital_amount,
            greffe_city=greffe_city,
        )

        return InpiCompanyInfo(
            siren=siren,
            company_name=company_name,
            legal_form=legal_form,
            capital_amount=float(capital_amount) if capital_amount is not None else None,
            capital_currency=capital_currency,
            greffe_city=greffe_city,
        )
