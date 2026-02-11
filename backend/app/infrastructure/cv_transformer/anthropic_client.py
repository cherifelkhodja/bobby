"""Anthropic Claude API client for CV data extraction.

Implements CvDataExtractorPort for dependency inversion.
"""

import asyncio
import json
import logging
import re
from typing import Any

from anthropic import Anthropic

from app.config import Settings
from app.infrastructure.cv_transformer.prompts import CV_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

# Structured CV data type
CvData = dict[str, Any]


class AnthropicClient:
    """Client for Anthropic Claude API to extract structured CV data."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    MAX_ATTEMPTS = 2

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

        Retries once on JSON parsing errors.

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

        last_error: Exception | None = None

        for attempt in range(self.MAX_ATTEMPTS):
            try:
                user_message = f"TEXTE DU CV A ANALYSER :\n\n{cv_text}"

                # Use asyncio.to_thread to avoid blocking the event loop
                response = await asyncio.to_thread(
                    client.messages.create,
                    model=model_to_use,
                    max_tokens=16384,
                    system=CV_EXTRACTION_PROMPT,
                    messages=[
                        {"role": "user", "content": user_message},
                    ],
                )

                # Check for truncation
                stop_reason = getattr(response, "stop_reason", None)
                if stop_reason == "max_tokens":
                    logger.warning(
                        "CV Transformer (Claude): response truncated (max_tokens)"
                    )

                # Extract text from response
                response_text = self._extract_response_text(response)
                if not response_text:
                    raise ValueError("La réponse de Claude est vide")

                # Clean and extract JSON from response
                json_text = self._nettoyer_reponse_json(response_text)

                # Parse JSON with repair fallback
                cv_data = self._parse_json_safe(json_text)

                # Validate required fields
                self._validate_cv_data(cv_data)

                if attempt > 0:
                    logger.info("CV Transformer (Claude): retry succeeded")
                return cv_data

            except Exception as e:
                if "API key" in str(e).lower() or "ANTHROPIC" in str(e):
                    raise
                last_error = e
                logger.warning(
                    f"CV Transformer (Claude) attempt {attempt + 1}/{self.MAX_ATTEMPTS} "
                    f"failed: {type(e).__name__}: {e}"
                )

        error_msg = str(last_error) if last_error else "Erreur inconnue"
        if isinstance(last_error, json.JSONDecodeError):
            raise ValueError(f"Erreur de parsing JSON: {error_msg}")
        raise ValueError(f"Erreur lors de l'extraction des données: {error_msg}")

    def _parse_json_safe(self, json_text: str) -> CvData:
        """Parse JSON with repair fallback for common LLM output issues."""
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            logger.info("JSON parse failed, attempting repair...")
            repaired = self._repair_json(json_text)
            return json.loads(repaired)

    def _repair_json(self, text: str) -> str:
        """Repair common JSON issues from LLM output."""
        # Fix trailing commas
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        # Fix truncated JSON by closing unclosed brackets
        stack: list[str] = []
        in_string = False
        escape_next = False

        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == "\\" and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in ("{", "["):
                stack.append(char)
            elif char == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif char == "]" and stack and stack[-1] == "[":
                stack.pop()

        if stack:
            closers = {"{": "}", "[": "]"}
            suffix = "".join(closers[b] for b in reversed(stack))
            logger.info(f"JSON repair: closing {len(stack)} unclosed bracket(s)")
            text += suffix

        return text

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
