"""Google Gemini API client for CV data extraction.

Implements CvDataExtractorPort for dependency inversion.
"""

import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import Settings


logger = logging.getLogger(__name__)

# Structured CV data type
CvData = dict[str, Any]

# Prompt for Gemini to extract CV data
CV_EXTRACTION_PROMPT = """
Tu es un expert en recrutement IT. Ta mission est de convertir le texte brut d'un CV en une structure JSON stricte.

RÈGLES IMPORTANTES :
1. Langue : FRANÇAIS uniquement.
2. Anonymisation : NE JAMAIS inclure l'email, le téléphone ou l'adresse du candidat.
3. CONCISION sur les compétences, mais EXHAUSTIVITÉ sur les expériences.
4. FORMAT DES DATES : Pour la PREMIÈRE expérience (la plus récente), utilise "Depuis Mois Année" (ex: "Depuis Mai 2024"). Pour les autres, utilise "Mois Année à Mois Année" (ex: "Janvier 2020 à Décembre 2022").
5. NOMS DES CLIENTS : Toujours utiliser le nom COMPLET de l'entreprise/client, JAMAIS de sigle seul (ex: "Crédit Agricole CIB" et non "CACIB", "Société Générale" et non "SG", "BNP Paribas" et non "BNPP"). Note: "CIB" est accepté pour "Corporate and Investment Bank".

RÈGLES POUR LES EXPÉRIENCES PROFESSIONNELLES :
- CONSERVER TOUTES les réalisations/tâches du CV original, ne rien supprimer.
- Si plusieurs missions chez le même client, créer une expérience par mission.
- Le contexte doit être détaillé (reprendre la description de la mission).
- Reformuler légèrement pour être professionnel mais NE PAS résumer excessivement.

RÈGLES POUR LES COMPÉTENCES :
- Si le CV contient déjà des compétences bien structurées (techniques, métiers, fonctionnelles), REPRENDS-LES TELLES QUELLES.
- Compétences techniques : CHOISIS les catégories les plus PERTINENTES selon le CV. NE CRÉE PAS de catégories vides ou avec "None". Inclus UNIQUEMENT les catégories où il y a des compétences réelles.
- Compétences métiers : UNIQUEMENT les secteurs d'activité majeurs (ex: Banque, Assurance, Retail). Maximum 2-3 items. Laisser vide [] si non pertinent.
- Compétences fonctionnelles : UNIQUEMENT les savoir-faire organisationnels clés (ex: Gestion de projet, Agilité). Maximum 2-3 items. Laisser vide [] si non pertinent.

FORMAT JSON ATTENDU :
{
  "profil": {
    "titre_cible": "String",
    "annees_experience": "String (ex: 5 ans)"
  },
  "resume_competences": {
    "techniques": {
       "Catégorie pertinente 1": "Valeurs séparées par virgules",
       "Catégorie pertinente 2": "Valeurs séparées par virgules"
    },
    "metiers": ["Secteur 1", "Secteur 2"],
    "fonctionnelles": ["Compétence 1", "Compétence 2"],
    "langues": ["Français : Natif", "Anglais : Courant"]
  },
  "formations": {
    "diplomes": [ {"annee": "2015", "libelle": "Master Informatique"} ],
    "certifications": [ {"annee": "2020", "libelle": "AWS Solutions Architect"} ]
  },
  "experiences": [
    {
      "client": "Nom du client ou entreprise",
      "periode": "Janvier 2020 à Décembre 2022 (ou 'Depuis Janvier 2023' si poste actuel)",
      "titre": "Poste occupé",
      "contexte": "Description courte du contexte (1-2 phrases)",
      "taches": {
        "Réalisations": ["Tâche 1", "Tâche 2", "Tâche 3"]
      },
      "environnement_technique": "Technologies utilisées séparées par des virgules"
    }
  ]
}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.

TEXTE DU CV À ANALYSER :
"""


class GeminiClient:
    """Client for Google Gemini API to extract structured CV data."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Gemini client.

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

    async def extract_cv_data(self, cv_text: str) -> CvData:
        """Extract structured data from CV text using Gemini.

        Args:
            cv_text: Raw text extracted from the CV document.

        Returns:
            Structured CV data as a dictionary.

        Raises:
            ValueError: If the API key is not configured or extraction fails.
        """
        self._configure()

        try:
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )

            prompt = CV_EXTRACTION_PROMPT + cv_text

            # Use asyncio.to_thread to avoid blocking the event loop
            response = await asyncio.to_thread(model.generate_content, prompt)

            # Extract text with fallback methods
            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("La réponse de Gemini est vide")

            # Clean and extract JSON from response
            json_text = self._nettoyer_reponse_json(response_text)

            # Parse JSON
            cv_data = json.loads(json_text)

            # Validate required fields
            self._validate_cv_data(cv_data)

            return cv_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de parsing JSON: {str(e)}")
        except Exception as e:
            if "API key" in str(e).lower() or "GEMINI" in str(e):
                raise
            raise ValueError(f"Erreur lors de l'extraction des données: {str(e)}")

    def _extract_response_text(self, response: Any) -> str | None:
        """Extract text from Gemini response with multiple fallback methods.

        Args:
            response: The GenerateContentResponse from Gemini.

        Returns:
            Extracted text or None if extraction fails.
        """
        # Method 1: Try standard .text property
        try:
            if hasattr(response, 'text'):
                text = response.text
                if text:
                    return text
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning(f"Standard response.text failed: {type(e).__name__}: {e}")

        # Method 2: Try accessing candidates directly
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text') and part.text:
                            return part.text
        except (KeyError, IndexError, AttributeError) as e:
            logger.warning(f"Candidate access failed: {type(e).__name__}: {e}")

        # Method 3: Try accessing parts directly from response
        try:
            if hasattr(response, 'parts') and response.parts:
                part = response.parts[0]
                if hasattr(part, 'text') and part.text:
                    return part.text
        except (KeyError, IndexError, AttributeError) as e:
            logger.warning(f"Parts access failed: {type(e).__name__}: {e}")

        # Method 4: Try to convert response to string and extract JSON
        try:
            response_str = str(response)
            if '{' in response_str and '}' in response_str:
                start = response_str.find('{')
                end = response_str.rfind('}')
                if start != -1 and end > start:
                    potential_json = response_str[start:end + 1]
                    json.loads(potential_json)
                    return potential_json
        except Exception as e:
            logger.warning(f"String extraction failed: {type(e).__name__}: {e}")

        logger.error(f"Failed to extract text. Response type: {type(response)}")
        return None

    def _validate_cv_data(self, data: CvData) -> None:
        """Validate the extracted CV data has required structure.

        Args:
            data: CV data to validate.

        Raises:
            ValueError: If required fields are missing.
        """
        required_fields = ["profil", "resume_competences", "formations", "experiences"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            raise ValueError(f"Champs manquants dans les données CV: {', '.join(missing)}")

        # Ensure experiences is a list
        if not isinstance(data.get("experiences"), list):
            data["experiences"] = []

        # Ensure formations has the right structure
        if "formations" in data:
            if not isinstance(data["formations"].get("diplomes"), list):
                data["formations"]["diplomes"] = []
            if not isinstance(data["formations"].get("certifications"), list):
                data["formations"]["certifications"] = []

    def _nettoyer_reponse_json(self, reponse_brute: str) -> str:
        """Clean Gemini response and extract valid JSON.

        Handles markdown code blocks and extracts JSON content.

        Args:
            reponse_brute: Raw response text from Gemini.

        Returns:
            Cleaned JSON string.
        """
        reponse = reponse_brute.strip()

        # Remove ```json at the beginning
        if reponse.startswith("```json"):
            reponse = reponse[7:]
        elif reponse.startswith("```"):
            reponse = reponse[3:]

        # Remove ``` at the end
        if reponse.endswith("```"):
            reponse = reponse[:-3]

        # Extract JSON between { and } (handles any extra text)
        debut = reponse.find('{')
        fin = reponse.rfind('}')
        if debut != -1 and fin != -1 and fin > debut:
            reponse = reponse[debut:fin + 1]

        return reponse.strip()
