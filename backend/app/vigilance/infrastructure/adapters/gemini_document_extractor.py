"""Automatic data extractor for vigilance documents.

Strategy:
- PDF files  : extract text with PyPDF2, then use regex (fast, deterministic).
               Falls back to Gemini if no relevant data found.
- Image files: always use Gemini Vision (JPEG, PNG).
- RIB        : regex for IBAN/BIC in PDFs, Gemini for images.
"""

from __future__ import annotations

import calendar
import io
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings

logger = logging.getLogger(__name__)

# ── Validity configuration ────────────────────────────────────────────────────

# Types where we extract the *issue* date and compute validity from months
_DATED_TYPES: dict[str, int] = {
    "kbis": 3,
    "extrait_insee": 3,
    "attestation_urssaf": 6,
    "attestation_fiscale": 6,
    "attestation_vigilance": 6,
    "certificat_regularite_fiscale": 6,
}

# Types where validity is determined by an explicit *expiry* date on the document
_EXPIRY_DATE_TYPES: set[str] = {"attestation_assurance_rc_pro"}

# ── French month mapping ──────────────────────────────────────────────────────

_MONTHS_FR: dict[str, int] = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

# ── Regex patterns ────────────────────────────────────────────────────────────

_RE_DATE_SLASH = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_RE_DATE_WORDS = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(_MONTHS_FR) + r")\s+(\d{4})\b",
    re.IGNORECASE,
)
_RE_IBAN = re.compile(
    r"\b([A-Z]{2}\d{2}(?:\s?\d{4}){4,7}(?:\s?[A-Z0-9]{1,4})?)\b",
    re.IGNORECASE,
)
_RE_BIC = re.compile(r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b")

# Context keywords used to classify date meaning
_EMISSION_KEYWORDS = (
    "délivrance", "délivré", "date of issue", "établi", "fait à",
    "fait le", "le :", "date de réalisation",
)
_VALIDITY_START_KEYWORDS = ("valable pour la période du", "à compter du")
_VALIDITY_END_KEYWORDS = ("jusqu'au", "valable jusqu", "au ", "expire", "expiration")
_UPDATE_KEYWORDS = ("à jour au", "au titre du")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    """Add N months to a date, clamping to the last day of the resulting month."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _extract_pdf_text(file_content: bytes) -> str:
    """Extract plain text from a PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader  # type: ignore[import-untyped]
        reader = PdfReader(io.BytesIO(file_content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("pdf_text_extraction_failed", error=str(exc))
        return ""


def _find_all_dates(text: str) -> list[dict[str, Any]]:
    """Find all dates in *text* together with their surrounding context."""
    found: list[dict[str, Any]] = []

    for match in _RE_DATE_SLASH.finditer(text):
        try:
            parsed = datetime.strptime(match.group(1), "%d/%m/%Y").date()
        except ValueError:
            continue
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 40)
        found.append({
            "date_str": match.group(1),
            "parsed": parsed,
            "context": text[start:end].replace("\n", " ").strip(),
        })

    for match in _RE_DATE_WORDS.finditer(text):
        jour_s, mois_s, annee_s = match.groups()
        mois_num = _MONTHS_FR.get(mois_s.lower())
        if not mois_num:
            continue
        try:
            parsed = date(int(annee_s), mois_num, int(jour_s))
        except ValueError:
            continue
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 40)
        found.append({
            "date_str": match.group(0),
            "parsed": parsed,
            "context": text[start:end].replace("\n", " ").strip(),
        })

    return found


def _classify_date(context: str) -> str:
    ctx = context.lower()
    if any(k in ctx for k in _EMISSION_KEYWORDS):
        return "emission"
    if any(k in ctx for k in _VALIDITY_START_KEYWORDS):
        return "validity_start"
    if any(k in ctx for k in _VALIDITY_END_KEYWORDS):
        return "validity_end"
    if any(k in ctx for k in _UPDATE_KEYWORDS):
        return "update"
    return "other"


def _pick_emission_date(dates: list[dict[str, Any]]) -> date | None:
    """Return the best candidate for the document issue/emission date."""
    # Prefer a date classified as emission or update
    for label in ("emission", "update"):
        for d in dates:
            if _classify_date(d["context"]) == label:
                return d["parsed"]
    # Fallback: pick the most recent date that is not in the future
    today = datetime.now(tz=timezone.utc).date()
    past_dates = [d["parsed"] for d in dates if d["parsed"] <= today]
    return max(past_dates) if past_dates else None


def _pick_expiry_date(dates: list[dict[str, Any]]) -> date | None:
    """Return the best candidate for the document expiry date."""
    for d in dates:
        if _classify_date(d["context"]) == "validity_end":
            return d["parsed"]
    # Fallback: pick the furthest future date
    today = datetime.now(tz=timezone.utc).date()
    future_dates = [d["parsed"] for d in dates if d["parsed"] > today]
    return max(future_dates) if future_dates else None


# ── Main extractor class ──────────────────────────────────────────────────────

class GeminiDocumentExtractor:
    """Hybrid extractor: regex for PDFs, Gemini Vision for images."""

    GEMINI_MODEL = "gemini-2.0-flash"

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.GEMINI_API_KEY
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY n'est pas configurée")
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    # ── Public interface ──────────────────────────────────────────

    async def extract(
        self,
        document_type: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Extract structured data from a vigilance document.

        Returns:
          - For RIB: {"beneficiaire": ..., "iban": ..., "bic": ...}
          - For dated types: {"document_date": "YYYY-MM-DD", "is_valid": bool|None}
          - For expiry-date types: {"document_date": None, "expiry_date": "YYYY-MM-DD", "is_valid": bool|None}
          - {} if type is not handled or extraction fails.
        """
        try:
            is_pdf = content_type == "application/pdf"

            if document_type == "rib":
                return self._extract_rib_regex(file_content) if is_pdf \
                    else await self._gemini_rib(file_content, content_type)

            if document_type in _DATED_TYPES:
                if is_pdf:
                    result = self._extract_dated_regex(document_type, file_content)
                    if result.get("document_date"):
                        return result
                return await self._gemini_dated(document_type, file_content, content_type)

            if document_type in _EXPIRY_DATE_TYPES:
                if is_pdf:
                    result = self._extract_expiry_regex(file_content)
                    if result.get("expiry_date") or result.get("is_valid") is not None:
                        return result
                return await self._gemini_expiry(file_content, content_type)

        except Exception as exc:
            logger.warning(
                "document_extraction_failed",
                document_type=document_type,
                error=str(exc),
            )
        return {}

    # ── Regex-based extractors (PDFs only) ────────────────────────

    def _extract_dated_regex(self, document_type: str, file_content: bytes) -> dict[str, Any]:
        text = _extract_pdf_text(file_content)
        dates = _find_all_dates(text)
        emission = _pick_emission_date(dates)
        today = datetime.now(tz=timezone.utc).date()
        is_valid: bool | None = None
        expiry_date: date | None = None

        if emission:
            validity_months = _DATED_TYPES[document_type]
            expiry_date = _add_months(emission, validity_months)
            is_valid = expiry_date >= today

        return {
            "document_date": emission.isoformat() if emission else None,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "is_valid": is_valid,
        }

    def _extract_expiry_regex(self, file_content: bytes) -> dict[str, Any]:
        text = _extract_pdf_text(file_content)
        dates = _find_all_dates(text)
        expiry = _pick_expiry_date(dates)
        today = datetime.now(tz=timezone.utc).date()
        is_valid: bool | None = None

        if expiry:
            is_valid = expiry >= today

        return {
            "document_date": None,
            "expiry_date": expiry.isoformat() if expiry else None,
            "is_valid": is_valid,
        }

    def _extract_rib_regex(self, file_content: bytes) -> dict[str, Any]:
        text = _extract_pdf_text(file_content)

        iban: str | None = None
        bic: str | None = None
        beneficiaire: str | None = None

        iban_match = _RE_IBAN.search(text)
        if iban_match:
            iban = re.sub(r"\s+", " ", iban_match.group(1)).upper().strip()

        bic_match = _RE_BIC.search(text)
        if bic_match:
            bic = bic_match.group(1).upper()

        # Heuristic: look for "Titulaire", "Bénéficiaire" or "Nom" labels
        for pattern in (
            r"(?:titulaire|bénéficiaire|nom du compte)[^\n:]*[:\s]+([A-ZÉÈÀÂÊÎÔÛÙÄËÏÖÜ][^\n]{2,50})",
            r"([A-Z][A-Z\s\-]{4,40})\s*\n.*?IBAN",
        ):
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                beneficiaire = m.group(1).strip()
                break

        return {
            "beneficiaire": beneficiaire,
            "iban": iban,
            "bic": bic,
        }

    # ── Gemini-based extractors (images + PDF fallback) ───────────

    async def _call_gemini(self, file_content: bytes, content_type: str, prompt: str) -> str:
        client = self._get_client()
        response = await client.aio.models.generate_content(
            model=self.GEMINI_MODEL,
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

    async def _gemini_rib(self, file_content: bytes, content_type: str) -> dict[str, Any]:
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

    async def _gemini_dated(
        self, document_type: str, file_content: bytes, content_type: str
    ) -> dict[str, Any]:
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

        expiry_date: date | None = None
        if document_date_str:
            try:
                document_date = date.fromisoformat(document_date_str)
                today = datetime.now(tz=timezone.utc).date()
                expiry_date = _add_months(document_date, _DATED_TYPES[document_type])
                is_valid = expiry_date >= today
            except ValueError:
                logger.warning("invalid_document_date_format", raw=document_date_str)

        return {
            "document_date": document_date.isoformat() if document_date else None,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "is_valid": is_valid,
        }

    async def _gemini_expiry(
        self, file_content: bytes, content_type: str
    ) -> dict[str, Any]:
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
