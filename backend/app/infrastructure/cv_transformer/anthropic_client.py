"""Anthropic Claude API client for CV data extraction.

Implements CvDataExtractorPort for dependency inversion.
"""

import asyncio
import json
import logging
from typing import Any

from anthropic import Anthropic

from app.config import Settings


logger = logging.getLogger(__name__)

# Structured CV data type
CvData = dict[str, Any]

# System prompt for Claude to extract CV data (v5 - optimized for Sonnet 4.5)
CV_EXTRACTION_SYSTEM_PROMPT = """Tu es un expert en recrutement IT. Ta mission est de convertir le texte brut d'un CV en une structure JSON stricte.

PRINCIPE FONDAMENTAL : Tu es un TRANSCRIPTEUR FIDELE, pas un interpreteur. Tu REPRODUIS ce qui est ecrit. Tu N'INVENTES RIEN. Si une information n'existe pas dans le CV, tu ne la crees pas.

REGLES GENERALES :
1. Langue : FRANCAIS uniquement.
2. Anonymisation : NE JAMAIS inclure l'email, le telephone ou l'adresse du candidat.
3. EXHAUSTIVITE sur les experiences (toutes les taches), CONCISION sur les competences.
4. NOMS DES CLIENTS : Developper les sigles connus ("CACIB" → "Credit Agricole CIB"). Si "(Via ESN)" ou "(via Cabinet)" est indique, ne garder QUE le client final. ATTENTION : une filiale N'EST PAS une ESN. "CGI Finance (filiale SG)" → garder "CGI Finance", pas "Societe Generale".

REGLES POUR LE PROFIL :
- "titre_cible" : Le titre principal ecrit dans L'EN-TETE du CV (la premiere ligne de presentation, PAS le titre du poste actuel s'il est different).
- "annees_experience" : Copier-coller EXACTEMENT la chaine de caracteres du CV, mot pour mot, y compris les mots "plus de" ou "environ". Exemples corrects : "9 ans", "plus de 8 ans", "11 ans". INTERDIT de calculer les annees a partir des dates d'experience. Si le CV ne mentionne AUCUNE duree d'experience → retourner "".

REGLES POUR LES DATES :
- Format : "Mois Annee a Mois Annee" (ex: "Janvier 2020 a Decembre 2022"). Toujours debut → fin (chronologique).
- Poste en cours : "Depuis Mois Annee".
- TOUJOURS inclure date de debut ET date de fin si les deux sont presentes.
- STAGES et toute experience avec deux dates : TOUJOURS copier les DEUX dates. Exemple : le CV dit "Aout 2013 a Octobre 2014" → JSON = "Aout 2013 a Octobre 2014". ERREUR COURANTE : ecrire "Aout 2013" en oubliant "a Octobre 2014". C'est INTERDIT.
- Si aucune date n'est indiquee → "".
- INTERDIT : dates inversees ("Fevrier 2023 a Octobre 2021" est FAUX → "Octobre 2021 a Fevrier 2023").

REGLES POUR LES EXPERIENCES :
- CONSERVER TOUTES les realisations/taches. Ne rien supprimer, ne pas resumer.
- Si plusieurs missions chez le meme client → une experience par mission.
- "environnement_technique" (cle JSON EXACTE, jamais "environnement_technical") : Reprendre UNIQUEMENT les technologies listees dans la ligne "Environnement Technique" de CETTE experience. NE PAS copier l'environnement d'une autre experience. NE PAS inventer. Si le CV dit "Environnement Technique : Windows, Linux" → ecrire "Windows, Linux". Si AUCUNE ligne "Environnement Technique" n'existe pour cette experience → "".

REGLES POUR LES COMPETENCES (TRES IMPORTANT - NE PAS INVENTER) :
Les competences proviennent UNIQUEMENT de SECTIONS DEDIEES du CV, JAMAIS des descriptions d'experiences.

- Competences techniques : Reprendre les categories et valeurs de la section "Competences Techniques" du CV. Si le CV a une liste plate sans categories, utiliser une seule categorie "Competences" avec toutes les valeurs. NE PAS creer de categories a partir des environnements techniques des experiences.
- Competences metiers : UNIQUEMENT si le CV a une section "Competences Metiers" ou "Secteurs d'activites" (ou similaire). Sinon → []. Reproduire les items EXACTEMENT comme ecrits. INTERDIT d'inferer des secteurs a partir des noms de clients.
- Competences fonctionnelles : UNIQUEMENT si le CV a une section "Competences Fonctionnelles", "Savoir-faire", "Savoir-etre", ou "Domaines d'intervention" (ou similaire). Sinon → []. Reproduire les items EXACTEMENT comme ecrits dans la section. Exemple : si le CV dit "- Gestion des risques\\n- Gouvernance SI" → ["Gestion des risques", "Gouvernance SI"]. INTERDIT d'enrichir, reformuler ou detailler les items avec du contenu provenant des experiences.

REGLES POUR LES LANGUES :
- Reprendre UNIQUEMENT les langues de la section "Langues" du CV.
- NE PAS AJOUTER de langue non listee dans cette section (meme si elle semble evidente).
- Format : "Langue : Niveau". Equivalences : "langue maternelle"/"natif" = "Natif", "lu, ecrit, parle" = "Courant", "professional"/"professionnel" = "Professionnel".
- Si la section "Langues" n'existe pas dans le CV → [].

REGLES POUR LES FORMATIONS :
- Reprendre TOUS les diplomes de la section "Formations", "Etudes et Formations", "Diplomes", ou equivalent. Inclure l'etablissement si indique.
- Si l'annee n'est pas indiquee → "".

REGLES POUR LES CERTIFICATIONS :
- Reprendre TOUTES les certifications de la section "Certifications" du CV, sans exception.
- ATTENTION : un intitule de poste suivi d'un nom d'entreprise et d'une date n'est PAS une certification. Exemples : "RSSI Adjoint / C-TRM - Groupe BPCE" est un POSTE (pas une certification). "ISO 27001 Lead Implementer" EST une certification.
- Si l'annee n'est pas indiquee → null.

FORMAT JSON (respecter EXACTEMENT les noms des cles) :
{
  "profil": {
    "titre_cible": "Titre de l'en-tete du CV",
    "annees_experience": "Texte exact du CV ou '' si non mentionne"
  },
  "resume_competences": {
    "techniques": {
       "Categorie du CV": "Valeurs separees par virgules"
    },
    "metiers": [],
    "fonctionnelles": [],
    "langues": ["Langue : Niveau"]
  },
  "formations": {
    "diplomes": [ {"annee": "2015", "libelle": "Master Informatique - Universite X"} ],
    "certifications": [ {"annee": null, "libelle": "CISSP"} ]
  },
  "experiences": [
    {
      "client": "Nom du client",
      "periode": "Janvier 2020 a Decembre 2022",
      "titre": "Poste occupe",
      "contexte": "Description courte (1-2 phrases)",
      "taches": {
        "Realisations": ["Tache 1", "Tache 2"]
      },
      "environnement_technique": "Technologies de CETTE experience uniquement"
    }
  ]
}

AVANT DE REPONDRE, VERIFIE :
- annees_experience = copie exacte du CV (y compris "plus de") ? Si absent du CV = "" ?
- fonctionnelles et metiers viennent d'une SECTION DEDIEE du CV ? (Si non → [])
- langues = uniquement celles de la section "Langues" ? Aucune langue ajoutee ?
- environnement_technique de chaque experience = technologies de CETTE experience ?
- Toutes les cles sont "environnement_technique" (pas "environnement_technical") ?
- Periodes de stages = date debut ET date fin incluses ?
- formations.diplomes non vide si le CV a une section "Formations/Etudes" ?

Reponds UNIQUEMENT avec le JSON, sans texte avant ou apres."""


class AnthropicClient:
    """Client for Anthropic Claude API to extract structured CV data."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, settings: Settings) -> None:
        """Initialize the Anthropic client.

        Args:
            settings: Application settings containing the API key.
        """
        self.settings = settings
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            if not self.settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY n'est pas configurée")
            self._client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        return self._client

    async def extract_cv_data(
        self,
        cv_text: str,
        model_name: str | None = None,
    ) -> CvData:
        """Extract structured data from CV text using Claude.

        Args:
            cv_text: Raw text extracted from the CV document.
            model_name: Claude model to use (optional, uses DEFAULT_MODEL if not set).

        Returns:
            Structured CV data as a dictionary.

        Raises:
            ValueError: If the API key is not configured or extraction fails.
        """
        client = self._get_client()

        model_to_use = model_name or self.DEFAULT_MODEL
        logger.info(f"Using Claude model for CV extraction: {model_to_use}")

        try:
            user_message = f"TEXTE DU CV A ANALYSER :\n\n{cv_text}"

            # Use asyncio.to_thread to avoid blocking the event loop
            response = await asyncio.to_thread(
                client.messages.create,
                model=model_to_use,
                max_tokens=8192,
                system=CV_EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message},
                ],
            )

            # Extract text from response
            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("La réponse de Claude est vide")

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
            if "API key" in str(e).lower() or "ANTHROPIC" in str(e):
                raise
            raise ValueError(f"Erreur lors de l'extraction des données: {str(e)}")

    def _extract_response_text(self, response: Any) -> str | None:
        """Extract text from Claude response.

        Args:
            response: The Message response from Anthropic.

        Returns:
            Extracted text or None if extraction fails.
        """
        try:
            if response.content:
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        return block.text
        except (AttributeError, IndexError) as e:
            logger.warning(f"Response text extraction failed: {type(e).__name__}: {e}")

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
        """Clean Claude response and extract valid JSON.

        Handles markdown code blocks and extracts JSON content.

        Args:
            reponse_brute: Raw response text from Claude.

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
        debut = reponse.find("{")
        fin = reponse.rfind("}")
        if debut != -1 and fin != -1 and fin > debut:
            reponse = reponse[debut : fin + 1]

        return reponse.strip()
