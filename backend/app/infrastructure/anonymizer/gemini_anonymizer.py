"""Google Gemini API client for opportunity anonymization.

Anonymizes job opportunity descriptions by removing client names,
internal project names, and proprietary information while preserving
technical skills and job context.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai

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

FORMAT DE SORTIE (JSON strict) :
{
  "title": "Titre anonymisé du poste",
  "description": "Description anonymisée et reformulée",
  "skills": ["Compétence1", "Compétence2", "Compétence3"]
}

ENTRÉE À ANONYMISER :
Titre: {title}
Description: {description}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""


class GeminiAnonymizer:
    """Client for Google Gemini API to anonymize opportunity descriptions."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Gemini anonymizer.

        Args:
            settings: Application settings containing the API key.
        """
        self.settings = settings
        self._configured = False

    def _configure(self) -> None:
        """Configure the Gemini API with credentials."""
        if not self._configured:
            if not self.settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY n'est pas configurée")
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            self._configured = True

    async def anonymize(
        self,
        title: str,
        description: str,
    ) -> AnonymizedOpportunity:
        """Anonymize an opportunity title and description.

        Args:
            title: Original opportunity title.
            description: Original opportunity description.

        Returns:
            AnonymizedOpportunity with anonymized title, description and extracted skills.

        Raises:
            ValueError: If the API key is not configured or anonymization fails.
        """
        self._configure()

        try:
            model = genai.GenerativeModel("gemini-2.5-flash-lite")

            prompt = ANONYMIZATION_PROMPT.format(
                title=title,
                description=description or "Pas de description disponible",
            )

            # Use asyncio.to_thread to avoid blocking the event loop
            response = await asyncio.to_thread(model.generate_content, prompt)

            if not response.text:
                raise ValueError("La réponse de Gemini est vide")

            # Clean and extract JSON from response
            json_text = self._clean_json_response(response.text)

            # Parse JSON
            data = json.loads(json_text)

            # Validate and extract fields
            anonymized_title = data.get("title", title)
            anonymized_description = data.get("description", description)
            skills = data.get("skills", [])

            if not isinstance(skills, list):
                skills = []

            return AnonymizedOpportunity(
                title=anonymized_title,
                description=anonymized_description,
                skills=skills,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error during anonymization: {e}")
            raise ValueError(f"Erreur de parsing JSON: {str(e)}")
        except Exception as e:
            if "API key" in str(e).lower() or "GEMINI" in str(e):
                raise
            logger.error(f"Error during anonymization: {e}")
            raise ValueError(f"Erreur lors de l'anonymisation: {str(e)}")

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
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            response = response[start:end + 1]
        else:
            # Log the problematic response for debugging
            logger.error(f"No valid JSON structure found in response: {response[:200]}")
            raise ValueError(f"Réponse Gemini invalide (pas de JSON trouvé)")

        return response.strip()
