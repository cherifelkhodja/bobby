"""Tests for GeminiAnonymizer with the new google-genai SDK.

Tests cover anonymization of opportunities, response parsing,
JSON cleaning, error handling, and the test_model method.
All external API calls are mocked using unittest.mock.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.anonymizer.gemini_anonymizer import (
    AnonymizedOpportunity,
    GeminiAnonymizer,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings with a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = "test-api-key-anonymizer"
    return settings


@pytest.fixture
def mock_settings_no_key():
    """Create mock settings without a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = ""
    return settings


@pytest.fixture
def sample_anonymized_response():
    """Return a valid anonymized opportunity JSON dict."""
    return {
        "title": "Developpeur Python pour grande banque francaise",
        "description": "Mission au sein d'un grand groupe bancaire pour un projet de transformation digitale.\n\nCompetences requises : Python, FastAPI, PostgreSQL.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    }


def _make_response(text: str):
    """Create a mock Gemini response with .text property."""
    response = MagicMock()
    response.text = text
    return response


def _make_response_no_text():
    """Create a mock Gemini response that has no usable text."""
    response = MagicMock()
    response.text = None
    response.candidates = []
    response.parts = []
    response.__str__ = lambda self: "EmptyResponse()"
    return response


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestGeminiAnonymizerInit:
    """Tests for GeminiAnonymizer initialization."""

    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    def test_client_initialized_with_correct_api_key(self, mock_genai, mock_settings):
        """Test that genai.Client is created with the correct API key."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        anonymizer = GeminiAnonymizer(mock_settings)
        result = anonymizer._get_client()

        mock_genai.Client.assert_called_once_with(api_key="test-api-key-anonymizer")
        assert result == mock_genai_client

    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    def test_client_is_cached(self, mock_genai, mock_settings):
        """Test that _get_client caches and reuses the client instance."""
        mock_genai.Client.return_value = MagicMock()

        anonymizer = GeminiAnonymizer(mock_settings)
        first = anonymizer._get_client()
        second = anonymizer._get_client()

        assert first is second
        mock_genai.Client.assert_called_once()

    def test_get_client_raises_when_no_api_key(self, mock_settings_no_key):
        """Test that _get_client raises ValueError when API key is missing."""
        anonymizer = GeminiAnonymizer(mock_settings_no_key)

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            anonymizer._get_client()


# ============================================================================
# anonymize Method Tests
# ============================================================================


class TestAnonymize:
    """Tests for the anonymize method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_calls_generate_content_with_correct_params(
        self, mock_genai, mock_settings, sample_anonymized_response
    ):
        """Test that anonymize calls generate_content with correct model and config."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(
            return_value=_make_response(json.dumps(sample_anonymized_response))
        )
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        await anonymizer.anonymize(
            title="Dev Python pour BNP Paribas",
            description="Mission chez BNP Paribas",
        )

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"
        # Verify the prompt contains the title and description
        assert "BNP Paribas" in call_kwargs.kwargs["contents"]

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_uses_custom_model(
        self, mock_genai, mock_settings, sample_anonymized_response
    ):
        """Test that a custom model name is passed to generate_content."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(
            return_value=_make_response(json.dumps(sample_anonymized_response))
        )
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        await anonymizer.anonymize("Title", "Description", model_name="gemini-1.5-pro")

        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-1.5-pro"

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_returns_anonymized_opportunity(
        self, mock_genai, mock_settings, sample_anonymized_response
    ):
        """Test that anonymize returns a properly structured AnonymizedOpportunity."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(
            return_value=_make_response(json.dumps(sample_anonymized_response))
        )
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.anonymize("Title", "Description")

        assert isinstance(result, AnonymizedOpportunity)
        assert result.title == "Developpeur Python pour grande banque francaise"
        assert "grand groupe bancaire" in result.description
        assert "Python" in result.skills
        assert "FastAPI" in result.skills
        assert len(result.skills) == 4

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_handles_markdown_wrapped_json(
        self, mock_genai, mock_settings, sample_anonymized_response
    ):
        """Test that JSON wrapped in markdown code blocks is parsed correctly."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        wrapped = "```json\n" + json.dumps(sample_anonymized_response) + "\n```"
        mock_generate = AsyncMock(return_value=_make_response(wrapped))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.anonymize("Title", "Description")

        assert isinstance(result, AnonymizedOpportunity)
        assert result.title == "Developpeur Python pour grande banque francaise"

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_empty_response_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that an empty Gemini response raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response_no_text())
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)

        with pytest.raises(ValueError, match="[Vv]ide|empty"):
            await anonymizer.anonymize("Title", "Description")

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_malformed_json_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that malformed JSON in response raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response("{not valid json at all"))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)

        with pytest.raises(ValueError, match="parsing JSON|essayer"):
            await anonymizer.anonymize("Title", "Description")

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_non_dict_response_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that a non-dict JSON response (e.g. array) raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response('["not", "a", "dict"]'))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)

        with pytest.raises(ValueError, match="objet JSON|inattendue"):
            await anonymizer.anonymize("Title", "Description")

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_falls_back_to_original_title_when_missing(
        self, mock_genai, mock_settings
    ):
        """Test fallback to original title when response is missing title field."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = {"description": "Some description", "skills": ["Python"]}
        mock_generate = AsyncMock(return_value=_make_response(json.dumps(response_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.anonymize("Original Title", "Original Description")

        assert result.title == "Original Title"

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_filters_empty_skills(self, mock_genai, mock_settings):
        """Test that empty/null skills are filtered out."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = {
            "title": "Dev Python",
            "description": "Description",
            "skills": ["Python", "", None, "FastAPI", 0],
        }
        mock_generate = AsyncMock(return_value=_make_response(json.dumps(response_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.anonymize("Title", "Desc")

        # Empty string, None, and 0 are falsy and should be filtered
        assert result.skills == ["Python", "FastAPI"]

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_handles_non_list_skills(self, mock_genai, mock_settings):
        """Test that non-list skills are replaced with empty list."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = {
            "title": "Dev Python",
            "description": "Description",
            "skills": "not a list",
        }
        mock_generate = AsyncMock(return_value=_make_response(json.dumps(response_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.anonymize("Title", "Desc")

        assert result.skills == []

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_generic_exception_wrapped(self, mock_genai, mock_settings):
        """Test that unexpected exceptions are wrapped in a user-friendly ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(side_effect=RuntimeError("Connection lost"))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)

        with pytest.raises(ValueError, match="inattendue|essayer"):
            await anonymizer.anonymize("Title", "Description")

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_anonymize_uses_fallback_description(
        self, mock_genai, mock_settings, sample_anonymized_response
    ):
        """Test that None description is replaced with fallback text in prompt."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(
            return_value=_make_response(json.dumps(sample_anonymized_response))
        )
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        await anonymizer.anonymize("Title", None)

        call_kwargs = mock_generate.call_args
        assert "Pas de description disponible" in call_kwargs.kwargs["contents"]


# ============================================================================
# test_model Method Tests
# ============================================================================


class TestTestModel:
    """Tests for the test_model method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_test_model_success(self, mock_genai, mock_settings):
        """Test successful model test returns success dict."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response('{"status": "ok"}'))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.test_model("gemini-2.0-flash")

        assert result["success"] is True
        assert result["model"] == "gemini-2.0-flash"
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], int)

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_test_model_failure_returns_error_dict(self, mock_genai, mock_settings):
        """Test that model test failure returns error dict instead of raising."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(side_effect=RuntimeError("Model not available"))
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.test_model("gemini-nonexistent")

        assert result["success"] is False
        assert result["model"] == "gemini-nonexistent"
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    @patch("app.infrastructure.anonymizer.gemini_anonymizer.genai")
    async def test_test_model_empty_response(self, mock_genai, mock_settings):
        """Test that empty response from model test returns failure."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response_no_text())
        mock_genai_client.aio.models.generate_content = mock_generate

        anonymizer = GeminiAnonymizer(mock_settings)
        result = await anonymizer.test_model("gemini-2.0-flash")

        assert result["success"] is False


# ============================================================================
# _clean_json_response Tests
# ============================================================================


class TestCleanJsonResponse:
    """Tests for the JSON response cleaning helper."""

    def test_strips_json_markdown_wrapper(self, mock_settings):
        """Test removal of ```json wrapper."""
        anonymizer = GeminiAnonymizer(mock_settings)
        raw = '```json\n{"key": "value"}\n```'

        result = anonymizer._clean_json_response(raw)

        assert json.loads(result) == {"key": "value"}

    def test_strips_plain_markdown_wrapper(self, mock_settings):
        """Test removal of plain ``` wrapper."""
        anonymizer = GeminiAnonymizer(mock_settings)
        raw = '```\n{"key": "value"}\n```'

        result = anonymizer._clean_json_response(raw)

        assert json.loads(result) == {"key": "value"}

    def test_extracts_json_from_surrounding_text(self, mock_settings):
        """Test extraction of JSON from text with extra content."""
        anonymizer = GeminiAnonymizer(mock_settings)
        raw = 'Voici le resultat: {"key": "value"} fin.'

        result = anonymizer._clean_json_response(raw)

        assert json.loads(result) == {"key": "value"}

    def test_raises_when_no_json_found(self, mock_settings):
        """Test that ValueError is raised when no JSON structure is found."""
        anonymizer = GeminiAnonymizer(mock_settings)

        with pytest.raises(ValueError, match="invalide|JSON"):
            anonymizer._clean_json_response("This is just text with no JSON at all")

    def test_handles_clean_json(self, mock_settings):
        """Test that already clean JSON passes through."""
        anonymizer = GeminiAnonymizer(mock_settings)
        raw = '{"title": "Dev Python", "description": "Desc", "skills": []}'

        result = anonymizer._clean_json_response(raw)

        parsed = json.loads(result)
        assert parsed["title"] == "Dev Python"


# ============================================================================
# _extract_response_text Tests
# ============================================================================


class TestAnonymizerExtractResponseText:
    """Tests for the _extract_response_text fallback logic in anonymizer."""

    def test_extracts_text_from_text_property(self, mock_settings):
        """Test extraction from standard .text property."""
        anonymizer = GeminiAnonymizer(mock_settings)
        response = _make_response('{"key": "value"}')

        result = anonymizer._extract_response_text(response)

        assert result == '{"key": "value"}'

    def test_extracts_text_from_candidates_fallback(self, mock_settings):
        """Test extraction via candidates[0].content.parts[0].text."""
        anonymizer = GeminiAnonymizer(mock_settings)

        part = SimpleNamespace(text='{"title": "Anonymized"}')
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        response = SimpleNamespace(text=None, candidates=[candidate])

        result = anonymizer._extract_response_text(response)

        assert result == '{"title": "Anonymized"}'

    def test_returns_none_for_empty_response(self, mock_settings):
        """Test that None is returned for completely empty response."""
        anonymizer = GeminiAnonymizer(mock_settings)
        response = _make_response_no_text()

        result = anonymizer._extract_response_text(response)

        assert result is None
