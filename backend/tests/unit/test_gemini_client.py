"""Tests for GeminiClient (CV transformer) with the new google-genai SDK.

Tests cover client initialization, CV data extraction, response parsing,
JSON cleaning, validation, and error handling. All external API calls
are mocked using unittest.mock.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.cv_transformer.gemini_client import GeminiClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings with a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = "test-api-key-123"
    return settings


@pytest.fixture
def mock_settings_no_key():
    """Create mock settings without a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = ""
    return settings


@pytest.fixture
def sample_cv_data():
    """Return a valid structured CV data dictionary."""
    return {
        "profil": {
            "titre_cible": "Developpeur Python Senior",
            "annees_experience": 10,
        },
        "resume_competences": {
            "techniques_list": [
                {"categorie": "Backend", "valeurs": "Python, FastAPI, Django"},
            ],
        },
        "formations": {
            "diplomes": [{"display": "Master Informatique"}],
            "certifications": [{"display": "AWS Solutions Architect"}],
        },
        "experiences": [
            {
                "client": "Grande banque francaise",
                "periode": "2020-2023",
                "titre": "Developpeur Python",
                "contexte": "Contexte de mission",
                "environnement_technique": "Python, FastAPI",
            },
        ],
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
    # Make str(response) return something without JSON
    response.__str__ = lambda self: "EmptyResponse()"
    return response


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestGeminiClientInit:
    """Tests for GeminiClient initialization and _get_client."""

    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    def test_client_initialized_with_correct_api_key(self, mock_genai, mock_settings):
        """Test that the genai.Client is created with the correct API key."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        client = GeminiClient(mock_settings)
        result = client._get_client()

        mock_genai.Client.assert_called_once_with(api_key="test-api-key-123")
        assert result == mock_genai_client

    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    def test_client_is_cached_after_first_creation(self, mock_genai, mock_settings):
        """Test that _get_client returns the same client on subsequent calls."""
        mock_genai.Client.return_value = MagicMock()

        client = GeminiClient(mock_settings)
        first_call = client._get_client()
        second_call = client._get_client()

        assert first_call is second_call
        mock_genai.Client.assert_called_once()

    def test_get_client_raises_when_no_api_key(self, mock_settings_no_key):
        """Test that _get_client raises ValueError when API key is missing."""
        client = GeminiClient(mock_settings_no_key)

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            client._get_client()


# ============================================================================
# extract_cv_data Tests
# ============================================================================


class TestExtractCvData:
    """Tests for the extract_cv_data method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_calls_generate_content_with_correct_params(
        self, mock_genai, mock_settings, sample_cv_data
    ):
        """Test that extract_cv_data calls generate_content with correct model and config."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(json.dumps(sample_cv_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)
        await client.extract_cv_data("Some CV text")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"
        assert "Some CV text" in call_kwargs.kwargs["contents"]

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_uses_custom_model(
        self, mock_genai, mock_settings, sample_cv_data
    ):
        """Test that a custom model name is passed through to generate_content."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(json.dumps(sample_cv_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)
        await client.extract_cv_data("CV text", model_name="gemini-1.5-pro")

        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-1.5-pro"

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_successful_json_parsing(
        self, mock_genai, mock_settings, sample_cv_data
    ):
        """Test successful extraction returns parsed CV data."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(json.dumps(sample_cv_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)
        result = await client.extract_cv_data("Some CV text")

        assert result["profil"]["titre_cible"] == "Developpeur Python Senior"
        assert len(result["experiences"]) == 1
        assert result["formations"]["diplomes"][0]["display"] == "Master Informatique"

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_handles_markdown_wrapped_json(
        self, mock_genai, mock_settings, sample_cv_data
    ):
        """Test that JSON wrapped in markdown code blocks is parsed correctly."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        wrapped = "```json\n" + json.dumps(sample_cv_data) + "\n```"
        mock_generate = AsyncMock(return_value=_make_response(wrapped))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)
        result = await client.extract_cv_data("Some CV text")

        assert result["profil"]["titre_cible"] == "Developpeur Python Senior"

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_empty_response_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that an empty Gemini response raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response_no_text())
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)

        with pytest.raises(ValueError, match="[Vv]ide|empty|extraction"):
            await client.extract_cv_data("Some CV text")

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_malformed_json_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that malformed JSON in response raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response("{not valid json"))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)

        with pytest.raises(ValueError, match="parsing JSON|extraction"):
            await client.extract_cv_data("Some CV text")

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_missing_required_fields_raises_value_error(
        self, mock_genai, mock_settings
    ):
        """Test that missing required fields in response raises ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        # Missing "formations" and "experiences"
        incomplete_data = {
            "profil": {"titre_cible": "Dev"},
            "resume_competences": {},
        }
        mock_generate = AsyncMock(return_value=_make_response(json.dumps(incomplete_data)))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)

        with pytest.raises(ValueError, match="[Cc]hamps manquants|missing"):
            await client.extract_cv_data("Some CV text")

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_api_error_re_raises(self, mock_genai, mock_settings):
        """Test that API errors with 'API key' in message are re-raised as-is."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(side_effect=ValueError("GEMINI_API_KEY n'est pas configuree"))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)

        with pytest.raises(ValueError, match="GEMINI"):
            await client.extract_cv_data("Some CV text")

    @pytest.mark.asyncio
    @patch("app.infrastructure.cv_transformer.gemini_client.genai")
    async def test_extract_cv_data_generic_exception_wrapped(self, mock_genai, mock_settings):
        """Test that generic exceptions are wrapped in ValueError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(side_effect=RuntimeError("Network timeout"))
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiClient(mock_settings)

        with pytest.raises(ValueError, match="extraction des donn"):
            await client.extract_cv_data("Some CV text")


# ============================================================================
# _extract_response_text Tests
# ============================================================================


class TestExtractResponseText:
    """Tests for the _extract_response_text fallback logic."""

    def test_extracts_text_from_text_property(self, mock_settings):
        """Test extraction from standard .text property."""
        client = GeminiClient(mock_settings)
        response = _make_response('{"key": "value"}')

        result = client._extract_response_text(response)

        assert result == '{"key": "value"}'

    def test_extracts_text_from_candidates(self, mock_settings):
        """Test extraction via candidates[0].content.parts[0].text fallback."""
        client = GeminiClient(mock_settings)

        part = SimpleNamespace(text='{"key": "value"}')
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        response = SimpleNamespace(text=None, candidates=[candidate])

        result = client._extract_response_text(response)

        assert result == '{"key": "value"}'

    def test_extracts_text_from_parts_directly(self, mock_settings):
        """Test extraction via response.parts[0].text fallback."""
        client = GeminiClient(mock_settings)

        part = SimpleNamespace(text='{"key": "value"}')
        response = SimpleNamespace(text=None, candidates=[], parts=[part])

        result = client._extract_response_text(response)

        assert result == '{"key": "value"}'

    def test_extracts_json_from_string_representation(self, mock_settings):
        """Test extraction via str(response) fallback for JSON content."""
        client = GeminiClient(mock_settings)

        class FakeResponse:
            text = None
            candidates = []
            parts = []

            def __str__(self):
                return 'Some wrapper text {"status": "ok"} more text'

        result = client._extract_response_text(FakeResponse())

        assert result == '{"status": "ok"}'

    def test_returns_none_for_completely_empty_response(self, mock_settings):
        """Test that None is returned when no text can be extracted."""
        client = GeminiClient(mock_settings)
        response = _make_response_no_text()

        result = client._extract_response_text(response)

        assert result is None


# ============================================================================
# _nettoyer_reponse_json Tests
# ============================================================================


class TestNettoyerReponseJson:
    """Tests for the JSON cleaning helper."""

    def test_strips_json_markdown_wrapper(self, mock_settings):
        """Test removal of ```json wrapper."""
        client = GeminiClient(mock_settings)
        raw = '```json\n{"key": "value"}\n```'

        result = client._nettoyer_reponse_json(raw)

        assert json.loads(result) == {"key": "value"}

    def test_strips_plain_markdown_wrapper(self, mock_settings):
        """Test removal of plain ``` wrapper."""
        client = GeminiClient(mock_settings)
        raw = '```\n{"key": "value"}\n```'

        result = client._nettoyer_reponse_json(raw)

        assert json.loads(result) == {"key": "value"}

    def test_extracts_json_from_surrounding_text(self, mock_settings):
        """Test extraction of JSON from text with leading/trailing content."""
        client = GeminiClient(mock_settings)
        raw = 'Here is the result: {"key": "value"} hope that helps!'

        result = client._nettoyer_reponse_json(raw)

        assert json.loads(result) == {"key": "value"}

    def test_handles_clean_json(self, mock_settings):
        """Test that already clean JSON passes through."""
        client = GeminiClient(mock_settings)
        raw = '{"key": "value"}'

        result = client._nettoyer_reponse_json(raw)

        assert json.loads(result) == {"key": "value"}

    def test_strips_whitespace(self, mock_settings):
        """Test that surrounding whitespace is stripped."""
        client = GeminiClient(mock_settings)
        raw = '   \n  {"key": "value"}  \n  '

        result = client._nettoyer_reponse_json(raw)

        assert json.loads(result) == {"key": "value"}


# ============================================================================
# _validate_cv_data Tests
# ============================================================================


class TestValidateCvData:
    """Tests for CV data validation."""

    def test_valid_data_passes(self, mock_settings, sample_cv_data):
        """Test that complete CV data passes validation."""
        client = GeminiClient(mock_settings)
        # Should not raise
        client._validate_cv_data(sample_cv_data)

    def test_missing_fields_raises(self, mock_settings):
        """Test that missing required fields raise ValueError."""
        client = GeminiClient(mock_settings)
        incomplete = {"profil": {}}

        with pytest.raises(ValueError, match="[Cc]hamps manquants"):
            client._validate_cv_data(incomplete)

    def test_non_list_experiences_converted(self, mock_settings):
        """Test that non-list experiences are converted to empty list."""
        client = GeminiClient(mock_settings)
        data = {
            "profil": {},
            "resume_competences": {},
            "formations": {"diplomes": [], "certifications": []},
            "experiences": "not a list",
        }

        client._validate_cv_data(data)

        assert data["experiences"] == []

    def test_missing_formations_sublists_initialized(self, mock_settings):
        """Test that missing diplomes/certifications lists are initialized."""
        client = GeminiClient(mock_settings)
        data = {
            "profil": {},
            "resume_competences": {},
            "formations": {},
            "experiences": [],
        }

        client._validate_cv_data(data)

        assert data["formations"]["diplomes"] == []
        assert data["formations"]["certifications"] == []
