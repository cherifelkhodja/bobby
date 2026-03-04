"""Extracteur de dates depuis les documents administratifs PDF.

Adapté du script d'extraction GEMINI. Utilise PyMuPDF (fitz) pour
l'extraction texte et des patterns regex pour l'identification des dates.
Aucune dépendance à un LLM externe — extraction déterministe et sans coût API.
"""
from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

import fitz  # PyMuPDF

from app.config import Settings

logger = logging.getLogger(__name__)

# ── Validité par type de document ────────────────────────────────────────────

# Types où la validité se calcule depuis la date d'émission (en mois)
_DATED_TYPES: dict[str, int] = {
    "kbis": 3,
    "extrait_insee": 3,
    "attestation_urssaf": 6,
    "attestation_fiscale": 6,
    "attestation_vigilance": 6,
    "certificat_regularite_fiscale": 6,
}

# Types où la validité est portée par une date d'expiration explicite
_EXPIRY_DATE_TYPES: set[str] = {"attestation_assurance_rc_pro"}

# ── Mapping mois français ────────────────────────────────────────────────────

_MONTHS_FR: dict[str, int] = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_months(d: date, months: int) -> date:
    """Ajoute N mois à une date, en clampant au dernier jour du mois résultant."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _extract_pdf_text(file_content: bytes) -> str:
    """Extrait le texte complet d'un PDF via PyMuPDF (fitz)."""
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as exc:
        logger.warning("pdf_text_extraction_failed", extra={"error": str(exc)})
        return ""


def _find_all_dates(text: str) -> list[dict[str, Any]]:
    """Trouve toutes les dates dans le texte avec leur contexte (±80 chars)."""
    found: list[dict[str, Any]] = []

    # Format JJ/MM/AAAA
    for match in re.finditer(r'\b(\d{2}/\d{2}/\d{4})\b', text):
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

    # Format "JJ mois AAAA" (ex: "26 juin 2025")
    pattern_mois = (
        r'\b(\d{1,2})\s+'
        r'(janvier|février|mars|avril|mai|juin|juillet|août'
        r'|septembre|octobre|novembre|décembre)\s+(\d{4})\b'
    )
    for match in re.finditer(pattern_mois, text, re.IGNORECASE):
        jour, mois_str, annee = match.groups()
        mois_num = _MONTHS_FR.get(mois_str.lower())
        if not mois_num:
            continue
        try:
            parsed = date(int(annee), mois_num, int(jour))
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
    """Classifie une date selon les mots-clés de son contexte."""
    ctx = context.lower()
    if any(k in ctx for k in ("délivrance", "délivré", "date of issue")):
        return "emission"
    if any(k in ctx for k in ("valable pour la période du", "à compter du")):
        return "validity_start"
    if any(k in ctx for k in ("jusqu'au", "valable jusqu", "expire", "expiration")):
        return "validity_end"
    if any(k in ctx for k in ("à jour au", "au titre du")):
        return "update"
    if any(k in ctx for k in ("établi", "fait à", "fait le", "le :")):
        return "emission"
    return "other"


def _pick_emission_date(dates: list[dict[str, Any]]) -> date | None:
    """Retourne la meilleure date d'émission/délivrance."""
    for label in ("emission", "update"):
        for d in dates:
            if _classify_date(d["context"]) == label:
                return d["parsed"]
    # Fallback : date passée la plus récente
    today = datetime.now(tz=timezone.utc).date()
    past_dates = [d["parsed"] for d in dates if d["parsed"] <= today]
    return max(past_dates) if past_dates else None


def _pick_expiry_date(dates: list[dict[str, Any]]) -> date | None:
    """Retourne la meilleure date d'expiration."""
    for d in dates:
        if _classify_date(d["context"]) == "validity_end":
            return d["parsed"]
    # Fallback : date future la plus lointaine
    today = datetime.now(tz=timezone.utc).date()
    future_dates = [d["parsed"] for d in dates if d["parsed"] > today]
    return max(future_dates) if future_dates else None


# ── Extracteur principal ──────────────────────────────────────────────────────

class DocumentExtractor:
    """Extracteur déterministe pour les documents de vigilance.

    Utilise PyMuPDF pour l'extraction texte et des regex pour les dates.
    Supporte uniquement les PDFs — les images retournent {}.
    """

    def __init__(self, settings: Settings) -> None:
        pass  # settings conservé pour compatibilité d'interface

    async def extract(
        self,
        document_type: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Extrait les données structurées d'un document de vigilance.

        Returns:
          - Pour RIB : {"beneficiaire": ..., "iban": ..., "bic": ...}
          - Pour types datés : {"document_date": "YYYY-MM-DD", "expiry_date": "YYYY-MM-DD", "is_valid": bool|None}
          - Pour types à expiration : {"document_date": None, "expiry_date": "YYYY-MM-DD", "is_valid": bool|None}
          - {} si type non supporté ou fichier non PDF.
        """
        if content_type != "application/pdf":
            return {}

        try:
            if document_type == "rib":
                return self._extract_rib(file_content)
            if document_type in _DATED_TYPES:
                return self._extract_dated(document_type, file_content)
            if document_type in _EXPIRY_DATE_TYPES:
                return self._extract_expiry(file_content)
        except Exception as exc:
            logger.warning(
                "document_extraction_failed",
                extra={"document_type": document_type, "error": str(exc)},
            )
        return {}

    # ── Extracteurs spécialisés ───────────────────────────────────

    def _extract_dated(self, document_type: str, file_content: bytes) -> dict[str, Any]:
        """KBIS, extrait INSEE, attestations URSSAF/fiscale/vigilance."""
        text = _extract_pdf_text(file_content)
        dates = _find_all_dates(text)
        emission = _pick_emission_date(dates)
        today = datetime.now(tz=timezone.utc).date()
        expiry_date: date | None = None
        is_valid: bool | None = None

        if emission:
            validity_months = _DATED_TYPES[document_type]
            expiry_date = _add_months(emission, validity_months)
            is_valid = expiry_date >= today

        return {
            "document_date": emission.isoformat() if emission else None,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "is_valid": is_valid,
        }

    def _extract_expiry(self, file_content: bytes) -> dict[str, Any]:
        """RC Pro et assurances — date d'expiration explicite."""
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

    def _extract_rib(self, file_content: bytes) -> dict[str, Any]:
        """RIB — IBAN, BIC, bénéficiaire."""
        text = _extract_pdf_text(file_content)

        iban: str | None = None
        bic: str | None = None
        beneficiaire: str | None = None

        iban_match = re.search(
            r'\b([A-Z]{2}\d{2}(?:\s?\d{4}){4,7}(?:\s?[A-Z0-9]{1,4})?)\b',
            text, re.IGNORECASE,
        )
        if iban_match:
            iban = re.sub(r'\s+', ' ', iban_match.group(1)).upper().strip()

        bic_match = re.search(r'\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b', text)
        if bic_match:
            bic = bic_match.group(1).upper()

        for pattern in (
            r'(?:titulaire|bénéficiaire|nom du compte)[^\n:]*[:\s]+([A-ZÉÈÀÂÊÎÔÛÙÄËÏÖÜ][^\n]{2,50})',
            r'([A-Z][A-Z\s\-]{4,40})\s*\n.*?IBAN',
        ):
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                beneficiaire = m.group(1).strip()
                break

        return {"beneficiaire": beneficiaire, "iban": iban, "bic": bic}


# Alias de rétrocompatibilité (les imports existants continuent de fonctionner)
GeminiDocumentExtractor = DocumentExtractor
