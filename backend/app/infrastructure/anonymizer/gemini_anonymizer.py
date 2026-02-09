"""Google Gemini API client for opportunity anonymization.

Anonymizes job opportunity descriptions by removing client names,
internal project names, and proprietary information while preserving
technical skills and job context.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class AnonymizedOpportunity:
    """Result of anonymizing an opportunity."""

    title: str
    description: str
    skills: list[str]


ANONYMIZATION_PROMPT = """Tu es un expert en recrutement IT. Ta mission est d'anonymiser des fiches de poste pour qu'elles puissent être partagées publiquement sans révéler d'informations confidentielles.

RÈGLES D'ANONYMISATION :
1. Remplace les noms de clients par des descriptions génériques :
   - "BNP Paribas" → "Grande banque française"
   - "Société Générale" → "Banque d'investissement internationale"
   - "AXA" → "Leader mondial de l'assurance"
   - "Orange" → "Opérateur télécom majeur"
   - "Airbus" → "Grand groupe aéronautique européen"
   - Utilise des descriptions similaires pour tout nom d'entreprise identifiable

2. Supprime ou généralise :
   - Noms de projets internes (ex: "Projet Phoenix" → "Projet de transformation digitale")
   - Acronymes propriétaires (ex: "SIFCA" → "système de gestion interne")
   - Noms d'équipes internes
   - Références à des outils internes spécifiques

3. CONSERVE tel quel :
   - Toutes les compétences techniques (Java, Python, AWS, Kubernetes, etc.)
   - Le contexte métier général (banque, assurance, retail, etc.)
   - La durée de la mission
   - Le niveau d'expérience requis
   - Les méthodologies (Agile, Scrum, etc.)

4. NE RIEN INVENTER :
   - Si une information n'est pas dans le texte original, ne l'ajoute pas
   - Reste fidèle au contenu technique

5. PRÉSERVE LA MISE EN FORME :
   - Conserve les sauts de ligne (\\n) pour séparer les paragraphes
   - Si le texte original contient des listes à puces, utilise des tirets (-) ou des puces (•) dans la sortie
   - Structure le texte en paragraphes distincts pour une meilleure lisibilité
   - Utilise des sauts de ligne entre les sections (contexte, missions, profil, etc.)

FORMAT DE SORTIE (JSON strict) :
{{
  "title": "Titre anonymisé du poste",
  "description": "Description anonymisée avec sauts de ligne (\\n) préservés",
  "skills": ["Compétence1", "Compétence2", "Compétence3"]
}}

ENTRÉE À ANONYMISER :
Titre: {title}
Description: {description}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""


class GeminiAnonymizer:
    """Client for Google Gemini API to anonymize opportunity descriptions."""

    # Available Gemini models for anonymization
    AVAILABLE_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, settings: Settings) -> None:
        """Initialize the Gemini anonymizer.

        Args:
            settings: Application settings containing the API key.
        """
        self.settings = settings
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Get or create the Gemini API client."""
        if self._client is None:
            if not self.settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY n'est pas configurée")
            self._client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
        return self._client

    async def test_model(self, model_name: str) -> dict:
        """Test a Gemini model with a simple prompt.

        Args:
            model_name: Name of the model to test.

        Returns:
            Dict with success status and response time.

        Raises:
            ValueError: If the test fails.
        """
        client = self._get_client()

        import time

        start_time = time.time()

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents='Réponds uniquement avec le JSON suivant: {"status": "ok"}',
            )
            elapsed = time.time() - start_time

            # Extract text with fallback
            text = self._extract_response_text(response)
            if not text:
                raise ValueError("Réponse vide")

            return {
                "success": True,
                "model": model_name,
                "response_time_ms": int(elapsed * 1000),
                "message": f"Modèle {model_name} fonctionnel",
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Model test failed for {model_name}: {e}")
            return {
                "success": False,
                "model": model_name,
                "response_time_ms": int(elapsed * 1000),
                "message": f"Erreur: {str(e)}",
            }

    async def anonymize(
        self,
        title: str,
        description: str,
        model_name: str | None = None,
    ) -> AnonymizedOpportunity:
        """Anonymize an opportunity title and description.

        Args:
            title: Original opportunity title.
            description: Original opportunity description.
            model_name: Gemini model to use (default: DEFAULT_MODEL).

        Returns:
            AnonymizedOpportunity with anonymized title, description and extracted skills.

        Raises:
            ValueError: If the API key is not configured or anonymization fails.
        """
        client = self._get_client()

        model_to_use = model_name or self.DEFAULT_MODEL
        logger.info(f"Using Gemini model: {model_to_use}")

        try:
            prompt = ANONYMIZATION_PROMPT.format(
                title=title,
                description=description or "Pas de description disponible",
            )

            # Use native async support from the new SDK
            response = await client.aio.models.generate_content(
                model=model_to_use,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            # Extract text from response with fallback methods
            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("La réponse de Gemini est vide")

            # Log raw response for debugging
            logger.debug(f"Raw Gemini response: {response_text[:500]}")

            # Clean and extract JSON from response
            json_text = self._clean_json_response(response_text)

            # Parse JSON
            data = json.loads(json_text)

            # Validate that data is a dict
            if not isinstance(data, dict):
                logger.error(f"Gemini returned non-dict JSON: {type(data)}")
                raise ValueError("La réponse Gemini n'est pas un objet JSON valide")

            # Validate and extract fields
            anonymized_title = data.get("title") or title
            anonymized_description = data.get("description") or description
            skills = data.get("skills", [])

            if not isinstance(skills, list):
                skills = []

            # Ensure skills are strings
            skills = [str(s) for s in skills if s]

            return AnonymizedOpportunity(
                title=anonymized_title,
                description=anonymized_description,
                skills=skills,
            )

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parsing error: {e}. JSON text was: {json_text[:200] if 'json_text' in locals() else 'N/A'}"
            )
            raise ValueError("Erreur de parsing JSON. Veuillez réessayer.")
        except ValueError:
            # Re-raise ValueError as-is (already formatted)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during anonymization: {type(e).__name__}: {e}")
            raise ValueError("Erreur inattendue lors de l'anonymisation. Veuillez réessayer.")

    def _extract_response_text(self, response: Any) -> str | None:
        """Extract text from Gemini response with multiple fallback methods.

        Args:
            response: The GenerateContentResponse from Gemini.

        Returns:
            Extracted text or None if extraction fails.
        """
        # Method 1: Try standard .text property
        try:
            if hasattr(response, "text"):
                text = response.text
                if text:
                    return text
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning(f"Standard response.text failed: {type(e).__name__}: {e}")

        # Method 2: Try accessing candidates directly
        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, "text") and part.text:
                            return part.text
        except (KeyError, IndexError, AttributeError) as e:
            logger.warning(f"Candidate access failed: {type(e).__name__}: {e}")

        # Method 3: Try accessing parts directly from response
        try:
            if hasattr(response, "parts") and response.parts:
                part = response.parts[0]
                if hasattr(part, "text") and part.text:
                    return part.text
        except (KeyError, IndexError, AttributeError) as e:
            logger.warning(f"Parts access failed: {type(e).__name__}: {e}")

        # Method 4: Try to convert response to string and extract JSON
        try:
            response_str = str(response)
            # Look for JSON-like content in string representation
            if "{" in response_str and "}" in response_str:
                start = response_str.find("{")
                end = response_str.rfind("}")
                if start != -1 and end > start:
                    potential_json = response_str[start : end + 1]
                    # Verify it's valid JSON
                    json.loads(potential_json)
                    return potential_json
        except Exception as e:
            logger.warning(f"String extraction failed: {type(e).__name__}: {e}")

        # Log response structure for debugging
        logger.error(f"Failed to extract text. Response type: {type(response)}")
        if hasattr(response, "__dict__"):
            logger.error(f"Response __dict__: {response.__dict__}")

        return None

    def _clean_json_response(self, raw_response: str) -> str:
        """Clean Gemini response and extract valid JSON.

        Handles markdown code blocks and extracts JSON content.

        Args:
            raw_response: Raw response text from Gemini.

        Returns:
            Cleaned JSON string.

        Raises:
            ValueError: If no valid JSON structure found.
        """
        response = raw_response.strip()

        # Remove ```json at the beginning
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        # Remove ``` at the end
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        # Extract JSON between { and } (handles any extra text)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            response = response[start : end + 1]
        else:
            # Log the problematic response for debugging
            logger.error(f"No valid JSON structure found in response: {response[:200]}")
            raise ValueError("Réponse Gemini invalide (pas de JSON trouvé)")

        return response.strip()
