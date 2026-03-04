"""Unit tests for InpiClient — auto-login, token cache, retry on 401."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.third_party.infrastructure.adapters.inpi_client as inpi_module
from app.third_party.infrastructure.adapters.inpi_client import (
    InpiClient,
    _get_inpi_token,
    _login_inpi,
)


# =============================================================================
# Helpers
# =============================================================================

def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock(status_code=status_code)
        )
    return resp


GEMINI_INPI_PAYLOAD = {
    "formality": {
        "content": {
            "personneMorale": {
                "identite": {
                    "entreprise": {
                        "denomination": "GEMINI",
                        "formeJuridique": "5710",
                    },
                    "description": {
                        "montantCapital": 10000,
                        "deviseCapital": "EUR",
                        "capitalVariable": False,
                    },
                },
                "adresseEntreprise": {
                    "adresse": {
                        "codePostal": "75008",
                        "commune": "PARIS",
                    }
                },
            }
        }
    }
}


# =============================================================================
# _login_inpi
# =============================================================================


class TestLoginInpi:
    @pytest.mark.asyncio
    async def test_login_success(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"token": "fresh-jwt"}

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _login_inpi("user@test.fr", "pass")

        assert result == "fresh-jwt"
        # Verify correct endpoint and body
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert "sso/login" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["username"] == "user@test.fr"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        mock_resp = MagicMock(status_code=401)

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _login_inpi("bad", "creds")

        assert result is None

    @pytest.mark.asyncio
    async def test_login_network_error(self):
        import httpx

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("timeout")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _login_inpi("user", "pass")

        assert result is None


# =============================================================================
# _get_inpi_token
# =============================================================================


class TestGetInpiToken:
    def setup_method(self):
        inpi_module._token_cache = None

    @pytest.mark.asyncio
    async def test_returns_cached_token(self):
        import time
        inpi_module._token_cache = ("cached-token", time.monotonic() + 3600)

        result = await _get_inpi_token("user", "pass", "static")

        assert result == "cached-token"

    @pytest.mark.asyncio
    async def test_refreshes_expired_cache(self):
        inpi_module._token_cache = ("old-token", 0.0)  # expired

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client._login_inpi",
            new=AsyncMock(return_value="new-token"),
        ):
            result = await _get_inpi_token("user", "pass", "")

        assert result == "new-token"
        assert inpi_module._token_cache is not None
        assert inpi_module._token_cache[0] == "new-token"

    @pytest.mark.asyncio
    async def test_falls_back_to_static_token(self):
        inpi_module._token_cache = None

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client._login_inpi",
            new=AsyncMock(return_value=None),
        ):
            result = await _get_inpi_token("user", "pass", "static-fallback")

        assert result == "static-fallback"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials_no_static(self):
        inpi_module._token_cache = None

        result = await _get_inpi_token("", "", "")

        assert result is None


# =============================================================================
# InpiClient.get_company
# =============================================================================


class TestInpiClientGetCompany:
    def setup_method(self):
        inpi_module._token_cache = ("test-token", 9999999999.0)

    @pytest.mark.asyncio
    async def test_returns_company_info(self):
        client = InpiClient(username="u", password="p")

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = GEMINI_INPI_PAYLOAD
            mock_resp.raise_for_status = MagicMock()
            mock_http.get.return_value = mock_resp
            mock_cls.return_value.__aenter__.return_value = mock_http

            result = await client.get_company("842799959")

        assert result is not None
        assert result.siren == "842799959"
        assert result.company_name == "GEMINI"
        assert result.legal_form_label == "SAS"
        assert result.capital_amount == 10000.0
        assert result.greffe_city == "Paris"

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        client = InpiClient(username="u", password="p")

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_cls:
            mock_http = AsyncMock()
            mock_http.get.return_value = MagicMock(status_code=404)
            mock_cls.return_value.__aenter__.return_value = mock_http

            result = await client.get_company("000000000")

        assert result is None

    @pytest.mark.asyncio
    async def test_retries_once_on_401(self):
        """On 401, invalidates cache, re-logins, retries — succeeds on second attempt."""
        client = InpiClient(username="u", password="p")

        success_resp = MagicMock(status_code=200)
        success_resp.json.return_value = GEMINI_INPI_PAYLOAD
        success_resp.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(status_code=401)
            return success_resp

        with patch(
            "app.third_party.infrastructure.adapters.inpi_client.httpx.AsyncClient"
        ) as mock_cls, patch(
            "app.third_party.infrastructure.adapters.inpi_client._get_inpi_token",
            new=AsyncMock(return_value="new-token"),
        ):
            mock_http = AsyncMock()
            mock_http.get.side_effect = mock_get
            mock_cls.return_value.__aenter__.return_value = mock_http

            result = await client.get_company("842799959")

        assert result is not None
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_when_no_token(self):
        inpi_module._token_cache = None
        client = InpiClient()  # no credentials, no static token

        result = await client.get_company("842799959")

        assert result is None
