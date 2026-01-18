"""Job posting anonymizer using Google Gemini.

Anonymizes job opportunity descriptions and restructures them
for Turnover-IT publication format, matching skills from the
Turnover-IT nomenclature.
"""

import asyncio
import json
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Optional

import google.generativeai as genai
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.database.models import TurnoverITSkillModel, TurnoverITSkillsMetadataModel
from app.infrastructure.turnoverit.client import TurnoverITClient


logger = logging.getLogger(__name__)


@dataclass
class AnonymizedJobPosting:
    """Result of anonymizing a job posting."""

    title: str
    description: str
    qualifications: str
    skills: list[str]  # Matched Turnover-IT skill slugs


# Skills sync interval (24 hours)
SKILLS_SYNC_INTERVAL = timedelta(hours=24)


JOB_POSTING_ANONYMIZATION_PROMPT = """Tu es un expert en recrutement IT. Ta mission est de réécrire des fiches de poste pour qu'elles soient publiables sur un job board (Turnover-IT) sans révéler d'informations confidentielles.

RÈGLES IMPORTANTES :
1. ANONYMISATION - Remplace sans mentir :
   - Les noms de clients → descriptions génériques ("Grande banque française", "Leader de l'assurance", "Groupe industriel international")
   - Les noms de projets internes → descriptions neutres ("projet de transformation", "programme d'évolution SI")
   - Les noms d'équipes → descriptions génériques ("équipe technique", "équipe projet")
   - Les outils propriétaires internes → descriptions génériques

2. NE JAMAIS MENTIR sur :
   - Les compétences techniques requises (Java, Python, AWS, etc.)
   - Le contexte métier général (banque, assurance, industrie...)
   - Le niveau d'expérience demandé
   - La durée ou localisation
   - Les méthodologies (Agile, Scrum...)

3. STRUCTURE TURNOVER-IT à respecter :

TITRE : Format "{{Métier}} (H/F)" - court et efficace
Exemples : "Développeur Java Senior (H/F)", "DevOps AWS (H/F)", "Chef de Projet Digital (H/F)"

DESCRIPTION DU POSTE (MINIMUM 500 caractères - OBLIGATOIRE) :
- Réécrire de façon détaillée le contexte de la mission (anonymisé)
- Décrire les missions principales de façon exhaustive
- Détailler les responsabilités
- Ne RIEN inventer, uniquement réécrire et reformuler le contenu original
- Utiliser des paragraphes et des listes pour une bonne lisibilité

PROFIL RECHERCHÉ (MINIMUM 150 caractères - OBLIGATOIRE) :
- Expérience attendue
- Compétences techniques requises
- Qualités et soft skills souhaités

4. SÉLECTION DES COMPÉTENCES (ANALYSE APPROFONDIE) :
Tu dois sélectionner UNIQUEMENT 3 à 6 compétences techniques parmi la liste fournie.
Critères de sélection :
- Pertinence : La compétence doit être DIRECTEMENT mentionnée ou CLAIREMENT requise dans le poste
- Importance : Privilégie les compétences PRINCIPALES, pas les secondaires
- Ne PAS inventer de compétences non mentionnées dans le poste original

Liste des compétences Turnover-IT disponibles :
{available_skills}

5. MISE EN FORME IMPORTANTE :
- Utilise des DOUBLES sauts de ligne (\\n\\n) entre les paragraphes et sections
- Utilise des tirets (-) pour les listes à puces
- Inclure des TITRES DE SECTIONS en MAJUSCULES suivis de " :"
- Structure claire avec des sections visibles

FORMAT EXACT ATTENDU POUR LA DESCRIPTION :
```
CONTEXTE DE LA MISSION :\\n\\n[Paragraphe décrivant le contexte anonymisé]\\n\\n

MISSIONS PRINCIPALES :\\n\\n- Mission 1\\n- Mission 2\\n- Mission 3\\n\\n

RESPONSABILITÉS :\\n\\n- Responsabilité 1\\n- Responsabilité 2\\n- Responsabilité 3
```

FORMAT EXACT ATTENDU POUR LE PROFIL RECHERCHÉ :
```
EXPÉRIENCE ATTENDUE :\\n\\n[Description de l'expérience requise]\\n\\n

COMPÉTENCES REQUISES :\\n\\n- Compétence 1\\n- Compétence 2\\n- Compétence 3\\n\\n

QUALITÉS SOUHAITÉES :\\n\\n- Qualité 1\\n- Qualité 2
```

FORMAT DE SORTIE (JSON strict) :
{{
  "title": "Titre du poste (H/F)",
  "description": "CONTEXTE DE LA MISSION :\\n\\n...\\n\\nMISSIONS PRINCIPALES :\\n\\n...\\n\\nRESPONSABILITÉS :\\n\\n...",
  "qualifications": "EXPÉRIENCE ATTENDUE :\\n\\n...\\n\\nCOMPÉTENCES REQUISES :\\n\\n...\\n\\nQUALITÉS SOUHAITÉES :\\n\\n...",
  "skills": ["skill-slug-1", "skill-slug-2", "skill-slug-3"]
}}

IMPORTANT pour les skills :
- Utilise les SLUGS exactement comme fournis dans la liste (ex: "java", "python", "aws")
- Sélectionne entre 3 et 6 skills maximum
- Ne mets QUE des skills présents dans la liste fournie

ENTRÉE À TRAITER :
Titre original: {title}
Client (à anonymiser): {client_name}
Description/Critères: {description}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""


class JobPostingAnonymizer:
    """Anonymizer for job postings using Gemini and Turnover-IT skills."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        settings: Settings,
        db_session: AsyncSession,
        turnoverit_client: Optional[TurnoverITClient] = None,
    ) -> None:
        """Initialize the job posting anonymizer.

        Args:
            settings: Application settings.
            db_session: Database session for skills cache.
            turnoverit_client: Optional TurnoverIT client for skills sync.
        """
        self.settings = settings
        self.db_session = db_session
        self.turnoverit_client = turnoverit_client or TurnoverITClient(settings)
        self._configured = False
        self._skills_cache: Optional[list[dict[str, str]]] = None

    def _configure(self) -> None:
        """Configure the Gemini API with credentials."""
        if not self._configured:
            if not self.settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY n'est pas configurée")
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            self._configured = True

    async def ensure_skills_synced(self) -> None:
        """Ensure skills are synced from Turnover-IT to database.

        Checks if sync is needed based on last sync time.
        Gracefully handles missing tables (migration not yet run).
        """
        try:
            # Check last sync time
            result = await self.db_session.execute(
                select(TurnoverITSkillsMetadataModel).where(TurnoverITSkillsMetadataModel.id == 1)
            )
            metadata = result.scalar_one_or_none()

            needs_sync = False
            if not metadata:
                needs_sync = True
            elif not metadata.last_synced_at:
                needs_sync = True
            elif datetime.now(timezone.utc) - metadata.last_synced_at > SKILLS_SYNC_INTERVAL:
                needs_sync = True
            elif metadata.total_skills == 0:
                needs_sync = True

            if needs_sync:
                await self.sync_skills()
        except Exception as e:
            # Table might not exist yet (migration not run) - log and continue
            logger.warning(f"Could not check skills sync status: {e}. Continuing without skills.")

    async def sync_skills(self) -> int:
        """Sync all skills from Turnover-IT API to database.

        Returns:
            Number of skills synced.
        """
        logger.info("Starting Turnover-IT skills sync...")

        # Fetch all skills from API
        skills = await self.turnoverit_client.fetch_all_skills()

        if not skills:
            logger.warning("No skills fetched from Turnover-IT")
            return 0

        # Clear existing skills
        await self.db_session.execute(delete(TurnoverITSkillModel))

        # Insert new skills
        for skill in skills:
            skill_model = TurnoverITSkillModel(
                name=skill["name"],
                slug=skill["slug"],
            )
            self.db_session.add(skill_model)

        # Update metadata
        result = await self.db_session.execute(
            select(TurnoverITSkillsMetadataModel).where(TurnoverITSkillsMetadataModel.id == 1)
        )
        metadata = result.scalar_one_or_none()

        if metadata:
            metadata.last_synced_at = datetime.now(timezone.utc)
            metadata.total_skills = len(skills)
        else:
            metadata = TurnoverITSkillsMetadataModel(
                id=1,
                last_synced_at=datetime.now(timezone.utc),
                total_skills=len(skills),
            )
            self.db_session.add(metadata)

        await self.db_session.commit()

        # Clear cache
        self._skills_cache = None

        logger.info(f"Synced {len(skills)} skills from Turnover-IT")
        return len(skills)

    async def get_cached_skills(self) -> list[dict[str, str]]:
        """Get skills from database cache.

        Returns:
            List of skills with name and slug. Empty list if table doesn't exist.
        """
        if self._skills_cache is not None:
            return self._skills_cache

        try:
            result = await self.db_session.execute(
                select(TurnoverITSkillModel).order_by(TurnoverITSkillModel.name)
            )
            skills = result.scalars().all()
            self._skills_cache = [{"name": s.name, "slug": s.slug} for s in skills]
        except Exception as e:
            # Table might not exist yet (migration not run) - return empty list
            logger.warning(f"Could not fetch skills from database: {e}. Using empty skills list.")
            self._skills_cache = []

        return self._skills_cache

    def match_skills_to_nomenclature(
        self,
        extracted_skills: list[str],
        turnoverit_skills: list[dict[str, str]],
        threshold: float = 0.7,
    ) -> list[str]:
        """Match extracted skills to Turnover-IT nomenclature.

        Uses fuzzy matching to find the best matches.

        Args:
            extracted_skills: Skills extracted by Gemini.
            turnoverit_skills: Turnover-IT skill list from database.
            threshold: Minimum similarity score for a match.

        Returns:
            List of matched Turnover-IT skill slugs.
        """
        matched_slugs: list[str] = []
        skill_name_to_slug = {s["name"].lower(): s["slug"] for s in turnoverit_skills}
        skill_names_lower = list(skill_name_to_slug.keys())

        for extracted in extracted_skills:
            extracted_lower = extracted.lower().strip()

            # Exact match first
            if extracted_lower in skill_name_to_slug:
                slug = skill_name_to_slug[extracted_lower]
                if slug not in matched_slugs:
                    matched_slugs.append(slug)
                continue

            # Fuzzy match
            best_match = None
            best_score = 0.0

            for skill_name in skill_names_lower:
                score = SequenceMatcher(None, extracted_lower, skill_name).ratio()
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = skill_name

            if best_match:
                slug = skill_name_to_slug[best_match]
                if slug not in matched_slugs:
                    matched_slugs.append(slug)
                    logger.debug(f"Matched '{extracted}' to '{best_match}' (score: {best_score:.2f})")

        return matched_slugs

    async def anonymize(
        self,
        title: str,
        description: str,
        client_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> AnonymizedJobPosting:
        """Anonymize a job posting and structure it for Turnover-IT.

        Args:
            title: Original opportunity title.
            description: Original opportunity description/criteria.
            client_name: Client name to anonymize.
            model_name: Gemini model to use.

        Returns:
            AnonymizedJobPosting with title, description, qualifications, and skills.

        Raises:
            ValueError: If anonymization fails.
        """
        self._configure()

        # Ensure skills are synced
        await self.ensure_skills_synced()

        # Get cached skills for the prompt
        turnoverit_skills = await self.get_cached_skills()

        # Format skills list for the prompt (name: slug format for clarity)
        skills_list_str = "\n".join(
            f"- {s['name']} (slug: {s['slug']})"
            for s in turnoverit_skills[:200]  # Limit to avoid token overflow
        )

        model_to_use = model_name or self.DEFAULT_MODEL
        logger.info(f"Anonymizing job posting with model: {model_to_use}")
        logger.info(f"Available skills for matching: {len(turnoverit_skills)}")

        try:
            model = genai.GenerativeModel(
                model_to_use,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )

            prompt = JOB_POSTING_ANONYMIZATION_PROMPT.format(
                title=title,
                client_name=client_name or "Non spécifié",
                description=description or "Pas de description disponible",
                available_skills=skills_list_str or "Aucune liste de compétences disponible",
            )

            response = await asyncio.to_thread(model.generate_content, prompt)

            # Extract response text
            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("La réponse de Gemini est vide")

            # Clean and parse JSON
            json_text = self._clean_json_response(response_text)
            data = json.loads(json_text)

            if not isinstance(data, dict):
                raise ValueError("La réponse Gemini n'est pas un objet JSON valide")

            # Extract fields
            anonymized_title = data.get("title") or f"{title} (H/F)"
            anonymized_description = data.get("description") or description
            qualifications = data.get("qualifications") or ""
            selected_skills = data.get("skills", [])

            if not isinstance(selected_skills, list):
                selected_skills = []

            # Validate description length (minimum 500 characters)
            if len(anonymized_description) < 500:
                logger.warning(
                    f"Description too short ({len(anonymized_description)} chars), "
                    f"minimum is 500 characters"
                )

            # Validate skills are from Turnover-IT nomenclature (use slugs directly)
            valid_slugs = {s["slug"] for s in turnoverit_skills}
            validated_skills = [
                skill for skill in selected_skills
                if skill in valid_slugs
            ]

            # Limit to 6 skills maximum
            validated_skills = validated_skills[:6]

            # If no valid skills found, try fuzzy matching as fallback
            if not validated_skills and selected_skills:
                logger.warning(
                    f"No exact slug matches found, trying fuzzy matching for: {selected_skills}"
                )
                validated_skills = self.match_skills_to_nomenclature(
                    selected_skills, turnoverit_skills
                )[:6]

            logger.info(
                f"Anonymized job posting: description={len(anonymized_description)} chars, "
                f"{len(selected_skills)} skills selected by Gemini, "
                f"{len(validated_skills)} validated against Turnover-IT"
            )

            return AnonymizedJobPosting(
                title=anonymized_title,
                description=anonymized_description,
                qualifications=qualifications,
                skills=validated_skills,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise ValueError("Erreur de parsing JSON. Veuillez réessayer.")
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during anonymization: {type(e).__name__}: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            # Include error type in message for debugging
            raise ValueError(f"Erreur lors de l'anonymisation ({type(e).__name__}). Veuillez réessayer.")

    def _extract_response_text(self, response) -> Optional[str]:
        """Extract text from Gemini response with fallback methods."""
        # Method 1: Standard .text property
        try:
            if hasattr(response, 'text') and response.text:
                return response.text
        except (KeyError, ValueError, AttributeError):
            pass

        # Method 2: Access candidates directly
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text') and part.text:
                            return part.text
        except (KeyError, IndexError, AttributeError):
            pass

        # Method 3: Try string conversion
        try:
            response_str = str(response)
            if '{' in response_str and '}' in response_str:
                start = response_str.find('{')
                end = response_str.rfind('}')
                if start != -1 and end > start:
                    potential_json = response_str[start:end + 1]
                    json.loads(potential_json)
                    return potential_json
        except Exception:
            pass

        return None

    def _clean_json_response(self, raw_response: str) -> str:
        """Clean Gemini response and extract valid JSON."""
        response = raw_response.strip()

        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            response = response[start:end + 1]
        else:
            raise ValueError("Réponse Gemini invalide (pas de JSON trouvé)")

        return response.strip()
