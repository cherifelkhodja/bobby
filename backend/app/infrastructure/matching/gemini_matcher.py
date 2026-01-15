"""Gemini-based CV matching service.

Uses Google Gemini AI to analyze CV text against job requirements
and calculate a matching score with detailed analysis.
"""

import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import Settings
from app.domain.exceptions import CvMatchingError

logger = logging.getLogger(__name__)


MATCHING_PROMPT = """Tu es un expert en recrutement IT. Analyse la correspondance entre ce CV et cette offre d'emploi.

Évalue sur une échelle de 0 à 100 :
- 0-30 : Peu de correspondance (compétences ou expérience très différentes)
- 31-50 : Correspondance partielle (quelques compétences communes)
- 51-70 : Bonne correspondance (profil intéressant avec quelques lacunes)
- 71-85 : Très bonne correspondance (profil solide)
- 86-100 : Excellente correspondance (profil idéal)

Critères d'évaluation :
1. Compétences techniques requises vs présentes dans le CV
2. Niveau d'expérience demandé vs expérience du candidat
3. Adéquation du parcours professionnel
4. Soft skills et qualités mentionnées

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{{
    "score": <entier entre 0 et 100>,
    "strengths": ["Point fort 1", "Point fort 2", "Point fort 3"],
    "gaps": ["Lacune 1", "Lacune 2"],
    "summary": "Résumé en 2-3 phrases de l'adéquation du profil"
}}

---

CV DU CANDIDAT :
{cv_text}

---

OFFRE D'EMPLOI :
{job_description}

---

JSON :"""


class GeminiMatchingService:
    """Service for CV matching using Google Gemini AI.

    This service analyzes candidate CVs against job descriptions
    and provides a matching score with detailed analysis.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize Gemini matching service.

        Args:
            settings: Application settings containing Gemini API key.
        """
        self.api_key = settings.GEMINI_API_KEY
        self._configured = False

    def _configure(self) -> None:
        """Configure Gemini API if not already done."""
        if not self._configured:
            if not self.api_key:
                raise CvMatchingError("Clé API Gemini non configurée")
            genai.configure(api_key=self.api_key)
            self._configured = True

    def _is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.api_key)

    async def calculate_match(
        self,
        cv_text: str,
        job_description: str,
    ) -> dict[str, Any]:
        """Calculate matching score between CV and job description.

        Args:
            cv_text: Extracted text from candidate's CV.
            job_description: Job posting description and requirements.

        Returns:
            Matching result dictionary with:
                - score: int (0-100)
                - strengths: list[str] - matching skills/experience
                - gaps: list[str] - missing requirements
                - summary: str - brief analysis summary

        Raises:
            CvMatchingError: If analysis fails.
        """
        if not self._is_configured():
            logger.warning("Gemini not configured, returning default score")
            return self._default_result()

        try:
            self._configure()

            # Truncate inputs to avoid token limits
            cv_text_truncated = cv_text[:10000] if cv_text else ""
            job_desc_truncated = job_description[:5000] if job_description else ""

            if not cv_text_truncated or not job_desc_truncated:
                logger.warning("Empty CV or job description")
                return self._default_result()

            prompt = MATCHING_PROMPT.format(
                cv_text=cv_text_truncated,
                job_description=job_desc_truncated,
            )

            # Use flash model for faster response
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Run synchronous API in thread pool
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent results
                    max_output_tokens=1000,
                ),
            )

            if not response.text:
                logger.warning("Empty response from Gemini")
                return self._default_result()

            # Parse JSON response
            result = self._parse_response(response.text)

            # Validate and normalize score
            result["score"] = max(0, min(100, result.get("score", 0)))

            logger.info(f"CV matching completed with score: {result['score']}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise CvMatchingError("Réponse invalide de l'IA")
        except Exception as e:
            logger.error(f"CV matching failed: {e}")
            raise CvMatchingError(f"Analyse échouée: {str(e)}")

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse and clean Gemini response to extract JSON.

        Args:
            response_text: Raw response from Gemini.

        Returns:
            Parsed JSON as dictionary.

        Raises:
            json.JSONDecodeError: If parsing fails.
        """
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        # Find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            text = text[start:end]

        return json.loads(text.strip())

    def _default_result(self) -> dict[str, Any]:
        """Return default result when matching cannot be performed."""
        return {
            "score": 0,
            "strengths": [],
            "gaps": ["Analyse non disponible"],
            "summary": "L'analyse automatique n'a pas pu être effectuée.",
        }

    async def health_check(self) -> bool:
        """Check if Gemini service is available.

        Returns:
            True if service is configured and accessible.
        """
        if not self._is_configured():
            return False

        try:
            self._configure()
            # Simple test to verify API key is valid
            model = genai.GenerativeModel("gemini-1.5-flash")
            await asyncio.to_thread(
                model.count_tokens,
                "test",
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
