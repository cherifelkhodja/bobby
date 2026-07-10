"""Tests for EmailService sender formatting (envoi depuis le domaine b0bby.fr).

Verrouille :
- l'adresse d'envoi reste toujours celle du domaine configuré (b0bby.fr),
  même quand une société émettrice fournit sa propre adresse ;
- le nom de la société émettrice est utilisé comme nom d'affichage ;
- l'adresse de la société part en Reply-To (et non en From).
"""

from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.infrastructure.email.sender import EmailService


def _make_service(**settings_overrides) -> EmailService:
    overrides = {
        "SMTP_FROM": "noreply@b0bby.fr",
        "RESEND_API_KEY": "",
        "FEATURE_EMAIL_NOTIFICATIONS": True,
        **settings_overrides,
    }
    return EmailService(Settings(**overrides))


class TestSenderFormatting:
    def test_sender_address_plain(self):
        service = _make_service()
        assert service._sender_address() == "noreply@b0bby.fr"

    def test_sender_address_with_display_name(self):
        service = _make_service(SMTP_FROM="Bobby <noreply@b0bby.fr>")
        assert service._sender_address() == "noreply@b0bby.fr"

    def test_format_sender_defaults_to_bobby(self):
        service = _make_service()
        assert service._format_sender() == "Bobby <noreply@b0bby.fr>"

    def test_format_sender_uses_company_name(self):
        service = _make_service()
        assert service._format_sender("Gemini Consulting") == (
            "Gemini Consulting <noreply@b0bby.fr>"
        )


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_company_email_goes_to_reply_to_not_from(self):
        """L'adresse de la société ne remplace pas le From : elle part en Reply-To."""
        service = _make_service()
        service._send_via_smtp = AsyncMock(return_value=True)

        await service._send_email(
            to="partner@example.com",
            subject="Test",
            html_body="<p>corps</p>",
            from_email="adv@geminiconsulting.fr",
            company_name="Gemini Consulting",
        )

        call = service._send_via_smtp.call_args
        assert call.args[3] == "Gemini Consulting <noreply@b0bby.fr>"  # sender
        assert call.args[4] == "adv@geminiconsulting.fr"  # reply_to

    @pytest.mark.asyncio
    async def test_no_reply_to_when_company_email_is_sender_address(self):
        service = _make_service()
        service._send_via_smtp = AsyncMock(return_value=True)

        await service._send_email(
            to="partner@example.com",
            subject="Test",
            html_body="<p>corps</p>",
            from_email="noreply@b0bby.fr",
        )

        call = service._send_via_smtp.call_args
        assert call.args[3] == "Bobby <noreply@b0bby.fr>"
        assert call.args[4] is None

    @pytest.mark.asyncio
    async def test_missing_recipient_is_skipped(self):
        """Un destinataire vide (ex: commercial_email absent) ne part pas en erreur SMTP."""
        service = _make_service()
        service._send_via_smtp = AsyncMock(return_value=True)

        result = await service._send_email(to="", subject="Test", html_body="x")

        assert result is False
        service._send_via_smtp.assert_not_called()
