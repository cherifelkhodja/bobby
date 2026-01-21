"""Gemini-based CV matching service.

Uses Google Gemini AI to analyze CV text against job requirements
and calculate a matching score with detailed analysis.
"""

import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field

from app.config import Settings
from app.domain.exceptions import CvMatchingError

logger = logging.getLogger(__name__)


# Pydantic models for structured matching response
class ScoresDetails(BaseModel):
    """Detailed scoring breakdown by category."""

    competences_techniques: int = Field(ge=0, le=100, description="Technical skills score (40% weight)")
    experience: int = Field(ge=0, le=100, description="Experience score (25% weight)")
    formation: int = Field(ge=0, le=100, description="Education score (15% weight)")
    soft_skills: int = Field(ge=0, le=100, description="Soft skills score (20% weight)")


class MatchingRecommendation(BaseModel):
    """Recommendation with action to take."""

    niveau: str = Field(description="Level: fort, moyen, faible")
    action_suggeree: str = Field(description="Suggested action to take")


class MatchingResult(BaseModel):
    """Complete matching result with detailed analysis."""

    score_global: int = Field(ge=0, le=100, description="Global weighted score")
    scores_details: ScoresDetails = Field(description="Detailed scores by category")
    competences_matchees: list[str] = Field(description="Matched competencies")
    competences_manquantes: list[str] = Field(description="Missing competencies")
    points_forts: list[str] = Field(description="Candidate strengths")
    points_vigilance: list[str] = Field(description="Points of concern")
    synthese: str = Field(description="Summary in 2-3 sentences")
    recommandation: MatchingRecommendation = Field(description="Recommendation")


MATCHING_SYSTEM_PROMPT = """Tu es un expert en recrutement IT spécialisé dans l'évaluation de candidatures.

Ton rôle est d'analyser la correspondance entre un CV de candidat et une offre d'emploi.

## Critères d'évaluation pondérés :

1. **Compétences techniques (40%)** : Correspondance entre les technologies/outils requis et ceux maîtrisés
2. **Expérience (25%)** : Années d'expérience, types de projets, secteurs d'activité
3. **Formation (15%)** : Diplômes, certifications pertinentes
4. **Soft skills (20%)** : Communication, travail d'équipe, adaptabilité mentionnés

## Échelle de notation (0-100) :
- 0-30 : Profil très éloigné des attentes
- 31-50 : Quelques compétences communes mais lacunes importantes
- 51-70 : Profil intéressant avec des axes de développement
- 71-85 : Bonne adéquation, profil solide
- 86-100 : Excellente correspondance, profil idéal

## Format de réponse JSON :

Tu dois répondre UNIQUEMENT avec un JSON valide suivant cette structure exacte :
{{
    "score_global": <entier 0-100>,
    "scores_details": {{
        "competences_techniques": <entier 0-100>,
        "experience": <entier 0-100>,
        "formation": <entier 0-100>,
        "soft_skills": <entier 0-100>
    }},
    "competences_matchees": ["compétence1", "compétence2", ...],
    "competences_manquantes": ["compétence1", "compétence2", ...],
    "points_forts": ["point fort 1", "point fort 2", "point fort 3"],
    "points_vigilance": ["point de vigilance 1", "point de vigilance 2"],
    "synthese": "Résumé en 2-3 phrases de l'adéquation du profil",
    "recommandation": {{
        "niveau": "fort|moyen|faible",
        "action_suggeree": "Action recommandée pour le recruteur"
    }}
}}

## Règles importantes :
- Sois objectif et factuel dans ton analyse
- Base-toi uniquement sur les informations présentes dans le CV et l'offre
- Le score global doit refléter la pondération des 4 critères
- Liste au maximum 5 compétences matchées et 5 manquantes
- Liste au maximum 3 points forts et 3 points de vigilance"""


MATCHING_USER_PROMPT = """Analyse la correspondance entre ce candidat et cette offre d'emploi.

---

## INFORMATIONS CANDIDAT :

**Intitulé de poste actuel** : {job_title}
**TJM souhaité** : {tjm_range}
**Disponibilité** : {availability}

---

## CV DU CANDIDAT :

{cv_text}

---

## OFFRE D'EMPLOI :

**Titre** : {job_title_offer}
**Description** : {job_description}
**Compétences requises** : {required_skills}

---

Analyse et retourne le JSON :"""


# Legacy prompt for backward compatibility
MATCHING_PROMPT_LEGACY = """Tu es un expert en recrutement IT. Analyse la correspondance entre ce CV et cette offre d'emploi.

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

    # Enhanced generation configuration for better precision
    ENHANCED_GENERATION_CONFIG = {
        "temperature": 0.1,  # Low temperature for consistent, deterministic results
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 1024,
        "response_mime_type": "application/json",
    }

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

    async def calculate_match_enhanced(
        self,
        cv_text: str,
        job_title_offer: str,
        job_description: str,
        required_skills: list[str] | None = None,
        candidate_job_title: str | None = None,
        candidate_tjm_range: str | None = None,
        candidate_availability: str | None = None,
    ) -> dict[str, Any]:
        """Calculate enhanced matching score with detailed analysis.

        Uses improved prompt with weighted criteria and structured output.

        Args:
            cv_text: Extracted text from candidate's CV.
            job_title_offer: Title of the job offer.
            job_description: Job posting description and requirements.
            required_skills: List of required skills for the position.
            candidate_job_title: Candidate's current job title from application.
            candidate_tjm_range: Candidate's expected daily rate range.
            candidate_availability: Candidate's availability date.

        Returns:
            Enhanced matching result dictionary with detailed scores.

        Raises:
            CvMatchingError: If analysis fails.
        """
        if not self._is_configured():
            logger.warning("Gemini not configured, returning default score")
            return self._default_result_enhanced()

        try:
            self._configure()

            # Truncate inputs to avoid token limits
            cv_text_truncated = cv_text[:10000] if cv_text else ""
            job_desc_truncated = job_description[:5000] if job_description else ""

            if not cv_text_truncated or not job_desc_truncated:
                logger.warning("Empty CV or job description")
                return self._default_result_enhanced()

            # Format skills list
            skills_str = ", ".join(required_skills) if required_skills else "Non spécifiées"

            # Build user prompt with candidate info
            user_prompt = MATCHING_USER_PROMPT.format(
                job_title=candidate_job_title or "Non renseigné",
                tjm_range=candidate_tjm_range or "Non renseigné",
                availability=candidate_availability or "Non renseignée",
                cv_text=cv_text_truncated,
                job_title_offer=job_title_offer,
                job_description=job_desc_truncated,
                required_skills=skills_str,
            )

            # Use flash model with system instruction
            model = genai.GenerativeModel(
                "gemini-2.5-flash-lite",
                system_instruction=MATCHING_SYSTEM_PROMPT,
            )

            # Run synchronous API in thread pool with enhanced config
            response = await asyncio.to_thread(
                model.generate_content,
                user_prompt,
                generation_config=genai.GenerationConfig(**self.ENHANCED_GENERATION_CONFIG),
            )

            if not response.text:
                logger.warning("Empty response from Gemini")
                return self._default_result_enhanced()

            # Parse and validate JSON response
            result = self._parse_enhanced_response(response.text)

            logger.info(f"Enhanced CV matching completed with score: {result['score_global']}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise CvMatchingError("Réponse invalide de l'IA")
        except Exception as e:
            logger.error(f"CV matching failed: {e}")
            raise CvMatchingError(f"Analyse échouée: {str(e)}")

    async def calculate_match(
        self,
        cv_text: str,
        job_description: str,
    ) -> dict[str, Any]:
        """Calculate matching score between CV and job description.

        This method maintains backward compatibility with the original format
        while internally using the enhanced matching system.

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

            prompt = MATCHING_PROMPT_LEGACY.format(
                cv_text=cv_text_truncated,
                job_description=job_desc_truncated,
            )

            # Use flash model for faster response
            model = genai.GenerativeModel("gemini-2.5-flash-lite")

            # Run synchronous API in thread pool with enhanced config for better consistency
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Lower temperature for more consistent results
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

    def _parse_enhanced_response(self, response_text: str) -> dict[str, Any]:
        """Parse and validate enhanced matching response from Gemini.

        Args:
            response_text: Raw response from Gemini (should be JSON).

        Returns:
            Validated and normalized matching result dictionary.

        Raises:
            json.JSONDecodeError: If parsing fails.
        """
        # First clean up response text (may still have markdown wrappers)
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

        # Parse JSON
        raw_result = json.loads(text.strip())

        # Validate and normalize using Pydantic model
        try:
            validated = MatchingResult.model_validate(raw_result)
            result = validated.model_dump()
        except Exception as e:
            logger.warning(f"Response validation failed, using raw result: {e}")
            # Fallback: use raw result with normalization
            result = self._normalize_enhanced_result(raw_result)

        # Ensure score_global is within bounds
        result["score_global"] = max(0, min(100, result.get("score_global", 0)))

        # Map to legacy format for backward compatibility
        result["score"] = result["score_global"]
        result["strengths"] = result.get("points_forts", [])
        result["gaps"] = result.get("competences_manquantes", [])
        result["summary"] = result.get("synthese", "")

        return result

    def _normalize_enhanced_result(self, raw_result: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw result to ensure all expected fields are present.

        Args:
            raw_result: Raw parsed JSON from Gemini.

        Returns:
            Normalized result with all expected fields.
        """
        # Ensure scores_details exists and has all fields
        scores_details = raw_result.get("scores_details", {})
        normalized_scores = {
            "competences_techniques": max(0, min(100, scores_details.get("competences_techniques", 0))),
            "experience": max(0, min(100, scores_details.get("experience", 0))),
            "formation": max(0, min(100, scores_details.get("formation", 0))),
            "soft_skills": max(0, min(100, scores_details.get("soft_skills", 0))),
        }

        # Ensure recommandation exists
        recommandation = raw_result.get("recommandation", {})
        normalized_reco = {
            "niveau": recommandation.get("niveau", "faible"),
            "action_suggeree": recommandation.get("action_suggeree", "À évaluer manuellement"),
        }

        return {
            "score_global": raw_result.get("score_global", 0),
            "scores_details": normalized_scores,
            "competences_matchees": raw_result.get("competences_matchees", [])[:5],
            "competences_manquantes": raw_result.get("competences_manquantes", [])[:5],
            "points_forts": raw_result.get("points_forts", [])[:3],
            "points_vigilance": raw_result.get("points_vigilance", [])[:3],
            "synthese": raw_result.get("synthese", "Analyse non disponible."),
            "recommandation": normalized_reco,
        }

    def _default_result(self) -> dict[str, Any]:
        """Return default result when matching cannot be performed."""
        return {
            "score": 0,
            "strengths": [],
            "gaps": ["Analyse non disponible"],
            "summary": "L'analyse automatique n'a pas pu être effectuée.",
        }

    def _default_result_enhanced(self) -> dict[str, Any]:
        """Return default enhanced result when matching cannot be performed."""
        return {
            "score_global": 0,
            "score": 0,  # Legacy compatibility
            "scores_details": {
                "competences_techniques": 0,
                "experience": 0,
                "formation": 0,
                "soft_skills": 0,
            },
            "competences_matchees": [],
            "competences_manquantes": [],
            "points_forts": [],
            "points_vigilance": ["Analyse non disponible"],
            "synthese": "L'analyse automatique n'a pas pu être effectuée.",
            "recommandation": {
                "niveau": "faible",
                "action_suggeree": "Vérifier la configuration Gemini",
            },
            # Legacy compatibility
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
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            await asyncio.to_thread(
                model.count_tokens,
                "test",
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
