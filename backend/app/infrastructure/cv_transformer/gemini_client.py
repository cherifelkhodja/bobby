"""Google Gemini API client for CV data extraction.

Implements CvDataExtractorPort for dependency inversion.
"""

import asyncio
import json
from typing import Any

import google.generativeai as genai

from app.config import Settings


# Structured CV data type
CvData = dict[str, Any]

# Prompt for Gemini to extract CV data
CV_EXTRACTION_PROMPT = """Tu es un expert en recrutement IT. Convertis le texte d'un CV en JSON structuré.

RÈGLES :
1. FRANÇAIS uniquement - traduis tout en français si nécessaire
2. ANONYMISATION : ne jamais inclure d'email, téléphone ou adresse du candidat
3. DATES : "Depuis Mois Année" pour le poste actuel, "Mois Année à Mois Année" pour les autres
4. NOMS COMPLETS des entreprises (pas de sigles seuls, développe-les)
5. EXHAUSTIF sur les expériences (inclure toutes les missions), CONCIS sur les compétences
6. Si une information n'est pas disponible, utilise une chaîne vide "" ou un tableau vide []

FORMAT JSON ATTENDU :
{
  "profil": {
    "titre_cible": "Titre du poste cible ou actuel",
    "annees_experience": "X ans"
  },
  "resume_competences": {
    "techniques": {
      "Langages": "Python, JavaScript, TypeScript",
      "Frameworks": "React, FastAPI, Django",
      "Cloud": "AWS, GCP, Azure",
      "Bases de données": "PostgreSQL, MongoDB",
      "Outils": "Docker, Kubernetes, Git"
    },
    "metiers": ["Banque", "Assurance", "E-commerce"],
    "fonctionnelles": ["Gestion de projet", "Agilité Scrum", "Leadership technique"],
    "langues": ["Français : Natif", "Anglais : Courant (B2/C1)"]
  },
  "formations": {
    "diplomes": [
      {"annee": "2015", "libelle": "Master Informatique - Université Paris-Saclay"}
    ],
    "certifications": [
      {"annee": "2020", "libelle": "AWS Solutions Architect Associate"}
    ]
  },
  "experiences": [
    {
      "client": "Nom complet du client/entreprise",
      "periode": "Depuis Janvier 2023",
      "titre": "Tech Lead / Développeur Senior",
      "contexte": "Description courte du contexte et des enjeux du projet",
      "taches": {
        "Réalisations": [
          "Conception et développement de l'architecture microservices",
          "Mise en place des pipelines CI/CD",
          "Encadrement d'une équipe de 5 développeurs"
        ]
      },
      "environnement_technique": "Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS"
    }
  ]
}

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
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = CV_EXTRACTION_PROMPT + cv_text + "\n\nRéponds UNIQUEMENT avec le JSON valide, sans commentaires ni explications."

            # Use asyncio.to_thread to avoid blocking the event loop
            response = await asyncio.to_thread(model.generate_content, prompt)

            if not response.text:
                raise ValueError("La réponse de Gemini est vide")

            # Extract JSON from response (handle markdown code blocks)
            json_text = response.text.strip()

            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                # Find the end of the opening code block marker
                first_newline = json_text.find("\n")
                if first_newline != -1:
                    json_text = json_text[first_newline + 1:]
                # Remove closing ```
                if json_text.endswith("```"):
                    json_text = json_text[:-3]
                json_text = json_text.strip()

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
