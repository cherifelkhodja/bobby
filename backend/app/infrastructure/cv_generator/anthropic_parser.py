"""Anthropic Claude parser for CV Generator (Beta).

Parses CV text into section-based JSON structure for frontend DOCX generation.
"""

import asyncio
import json
import logging
from typing import Any

from anthropic import Anthropic

from app.config import Settings
from app.infrastructure.cv_generator.prompts import CV_GENERATOR_PROMPT

logger = logging.getLogger(__name__)


class CvGeneratorParser:
    """Parse CV text into section-based JSON using Claude."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            if not self.settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY n'est pas configurée")
            self._client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        return self._client

    async def parse_cv(
        self,
        cv_text: str,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Parse CV text into section-based JSON structure.

        Args:
            cv_text: Raw text extracted from the CV document.
            model_name: Claude model to use (optional).

        Returns:
            Section-based CV data with keys: header, sections.

        Raises:
            ValueError: If parsing fails.
        """
        client = self._get_client()
        model_to_use = model_name or self.DEFAULT_MODEL
        logger.info(f"CV Generator parsing with model: {model_to_use}")

        try:
            user_message = f"CV A PARSER :\n\n{cv_text}"

            response = await asyncio.to_thread(
                client.messages.create,
                model=model_to_use,
                max_tokens=8192,
                system=CV_GENERATOR_PROMPT,
                messages=[
                    {"role": "user", "content": user_message},
                ],
            )

            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("La réponse de Claude est vide")

            json_text = self._nettoyer_reponse_json(response_text)
            cv_data = json.loads(json_text)
            self._validate_cv_data(cv_data)

            return cv_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de parsing JSON: {str(e)}")
        except Exception as e:
            if "API key" in str(e).lower() or "ANTHROPIC" in str(e):
                raise
            raise ValueError(f"Erreur lors du parsing CV: {str(e)}")

    def _extract_response_text(self, response: Any) -> str | None:
        """Extract text from Claude response."""
        try:
            if response.content:
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        return block.text
        except (AttributeError, IndexError) as e:
            logger.warning(f"Response text extraction failed: {type(e).__name__}: {e}")

        logger.error(f"Failed to extract text. Response type: {type(response)}")
        return None

    def _validate_cv_data(self, data: dict[str, Any]) -> None:
        """Validate section-based CV data structure.

        Raises:
            ValueError: If required fields are missing.
        """
        if "header" not in data:
            raise ValueError("Champ 'header' manquant dans les données CV")

        if "sections" not in data or not isinstance(data["sections"], list):
            raise ValueError("Champ 'sections' manquant ou invalide")

        # Ensure header has required fields
        header = data["header"]
        if "titre" not in header:
            header["titre"] = ""
        if "experience" not in header:
            header["experience"] = ""

    def _nettoyer_reponse_json(self, reponse_brute: str) -> str:
        """Clean Claude response and extract valid JSON."""
        reponse = reponse_brute.strip()

        if reponse.startswith("```json"):
            reponse = reponse[7:]
        elif reponse.startswith("```"):
            reponse = reponse[3:]

        if reponse.endswith("```"):
            reponse = reponse[:-3]

        debut = reponse.find("{")
        fin = reponse.rfind("}")
        if debut != -1 and fin != -1 and fin > debut:
            reponse = reponse[debut : fin + 1]

        return reponse.strip()
