"""Gemini-based automatic data extractor for vigilance documents."""

from __future__ import annotations

import calendar
import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings

logger = logging.getLogger(__name__)

# Document types where we extract the issue date and compute validity from months
_DATED_TYPES: dict[str, int] = {
    "kbis": 3,
    "extrait_insee": 3,
    "attestation_urssaf": 6,
    "attestation_fiscale": 6,
    "attestation_vigilance": 6,
    "certificat_regularite_fiscale": 6,
}

# Document types where validity is determined by an explicit expiry date on the document
_EXPIRY_DATE_TYPES: set[str] = {"attestation_assurance_rc_pro"}


def _add_months(d: date, months: int) -> date:
    """Add a number of months to a date, clamping to the last day of the month."""
    total_month = d.month - 1 + months
    year = d.year + total_month // 12
    month = total_month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class GeminiDocumentExtractor:
    """Extracts structured data from vigilance documents using Gemini Vision."""

    MODEL = "gemini-2.0-flash"

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY n'est pas configurée")
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def extract(
        self,
        document_type: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Extract relevant data from a vigilance document.

        Returns a dict with:
          - For RIB: {"beneficiaire": ..., "iban": ..., "bic": ...}
          - For dated types: {"document_date": "YYYY-MM-DD", "is_valid": bool|None}
          - For expiry-date types: {"document_date": None, "expiry_date": "YYYY-MM-DD", "is_valid": bool|None}
          - Empty dict if type is not handled or extraction fails.
        """
        try:
            if document_type == "rib":
                return await self._extract_rib(file_content, content_type)
            if document_type in _DATED_TYPES:
                return await self._extract_dated(document_type, file_content, content_type)
            if document_type in _EXPIRY_DATE_TYPES:
                return await self._extract_expiry_date(document_type, file_content, content_type)
        except Exception as exc:
            logger.warning(
                "gemini_document_extraction_failed",
                document_type=document_type,
                error=str(exc),
            )
        return {}

    # ── Private helpers ───────────────────────────────────────────

    async def _call_gemini(self, file_content: bytes, content_type: str, prompt: str) -> str:
        """Send file + prompt to Gemini and return raw response text."""
        client = self._get_client()
        response = await client.aio.models.generate_content(
            model=self.MODEL,
            contents=[
                types.Part.from_bytes(data=file_content, mime_type=content_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        if hasattr(response, "text") and response.text:
            return response.text
        try:
            return response.candidates[0].content.parts[0].text
        except Exception:
            return str(response)

    async def _extract_rib(self, file_content: bytes, content_type: str) -> dict[str, Any]:
        """Extract IBAN, BIC and beneficiary from a RIB."""
        prompt = (
            "Analyse ce RIB (Relevé d'Identité Bancaire) et extrais les informations suivantes.\n"
            "Réponds UNIQUEMENT avec un JSON valide, sans markdown ni texte autour.\n"
            "{\n"
            '  "beneficiaire": "Nom complet du titulaire du compte",\n'
            '  "iban": "FRXX XXXX XXXX XXXX XXXX XXXX XXX",\n'
            '  "bic": "XXXXXXXXX"\n'
            "}\n"
            "Si une information est absente, utilise null pour ce champ."
        )
        raw = await self._call_gemini(file_content, content_type, prompt)
        data = json.loads(raw)
        return {
            "beneficiaire": data.get("beneficiaire"),
            "iban": data.get("iban"),
            "bic": data.get("bic"),
        }

    async def _extract_dated(
        self, document_type: str, file_content: bytes, content_type: str
    ) -> dict[str, Any]:
        """Extract issue date from an official dated document, then compute validity."""
        validity_months = _DATED_TYPES[document_type]
        prompt = (
            "Analyse ce document officiel et extrais sa date d'émission ou de délivrance.\n"
            "Réponds UNIQUEMENT avec un JSON valide, sans markdown ni texte autour.\n"
            "{\n"
            '  "document_date": "YYYY-MM-DD"\n'
            "}\n"
            "Si aucune date n'est trouvée, utilise null."
        )
        raw = await self._call_gemini(file_content, content_type, prompt)
        data = json.loads(raw)

        document_date_str: str | None = data.get("document_date")
        document_date: date | None = None
        is_valid: bool | None = None

        if document_date_str:
            try:
                document_date = date.fromisoformat(document_date_str)
                today = datetime.now(tz=timezone.utc).date()
                expiry = _add_months(document_date, validity_months)
                is_valid = expiry >= today
            except ValueError:
                logger.warning("invalid_document_date_format", raw=document_date_str)

        return {
            "document_date": document_date.isoformat() if document_date else None,
            "is_valid": is_valid,
        }

    async def _extract_expiry_date(
        self, document_type: str, file_content: bytes, content_type: str
    ) -> dict[str, Any]:
        """Extract the explicit expiry date from a document (e.g. RC Pro)."""
        prompt = (
            "Analyse ce document et extrais sa date de fin de validité "
            "(date d'expiration ou d'échéance de la couverture).\n"
            "Réponds UNIQUEMENT avec un JSON valide, sans markdown ni texte autour.\n"
            "{\n"
            '  "expiry_date": "YYYY-MM-DD"\n'
            "}\n"
            "Si aucune date d'expiration n'est trouvée, utilise null."
        )
        raw = await self._call_gemini(file_content, content_type, prompt)
        data = json.loads(raw)

        expiry_date_str: str | None = data.get("expiry_date")
        expiry_date: date | None = None
        is_valid: bool | None = None

        if expiry_date_str:
            try:
                expiry_date = date.fromisoformat(expiry_date_str)
                today = datetime.now(tz=timezone.utc).date()
                is_valid = expiry_date >= today
            except ValueError:
                logger.warning("invalid_expiry_date_format", raw=expiry_date_str)

        return {
            "document_date": None,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "is_valid": is_valid,
        }
