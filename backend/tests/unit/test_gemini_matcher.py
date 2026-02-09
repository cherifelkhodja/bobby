"""Tests for GeminiMatchingService with the new google-genai SDK.

Tests cover enhanced matching, legacy matching, CV quality evaluation,
health check, response parsing, normalization, and error handling.
All external API calls are mocked using unittest.mock.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.exceptions import CvMatchingError
from app.infrastructure.matching.gemini_matcher import GeminiMatchingService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings with a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = "test-api-key-matcher"
    return settings


@pytest.fixture
def mock_settings_no_key():
    """Create mock settings without a Gemini API key."""
    settings = MagicMock()
    settings.GEMINI_API_KEY = ""
    return settings


@pytest.fixture
def sample_enhanced_response():
    """Return a valid enhanced matching response JSON string."""
    return json.dumps(
        {
            "score_global": 72,
            "scores_details": {
                "competences_techniques": 80,
                "experience": 70,
                "formation": 60,
                "soft_skills": 65,
            },
            "competences_matchees": ["Python", "FastAPI", "PostgreSQL"],
            "competences_manquantes": ["Kubernetes", "Terraform"],
            "points_forts": [
                "Solide experience Python",
                "Bonne connaissance des APIs REST",
            ],
            "points_vigilance": ["Pas d'experience cloud native"],
            "synthese": "Profil solide en developpement Python avec bonne experience.",
            "recommandation": {
                "niveau": "fort",
                "action_suggeree": "Proposer un entretien technique",
            },
        }
    )


@pytest.fixture
def sample_legacy_response():
    """Return a valid legacy matching response JSON string."""
    return json.dumps(
        {
            "score": 65,
            "strengths": ["Python", "REST APIs"],
            "gaps": ["Cloud experience"],
            "summary": "Bon profil backend mais manque d'experience cloud.",
        }
    )


@pytest.fixture
def sample_cv_quality_response():
    """Return a valid CV quality evaluation response JSON string."""
    return json.dumps(
        {
            "niveau_experience": "SENIOR",
            "annees_experience": 10.0,
            "note_globale": 15.5,
            "details_notes": {
                "stabilite_missions": {
                    "note": 7,
                    "max": 8,
                    "duree_moyenne_mois": 24,
                    "commentaire": "Bonnes durees de mission",
                },
                "qualite_comptes": {
                    "note": 5,
                    "max": 6,
                    "comptes_identifies": ["BNP Paribas", "Societe Generale"],
                    "commentaire": "Grands comptes CAC40",
                },
                "parcours_scolaire": {
                    "note": 1.5,
                    "max": 2,
                    "formations_identifiees": ["EPITA"],
                    "commentaire": "Bonne ecole d'ingenieur",
                },
                "continuite_parcours": {
                    "note": 3,
                    "max": 4,
                    "trous_identifies": ["6 mois en 2019"],
                    "commentaire": "Un trou moyen",
                },
                "bonus_malus": {
                    "valeur": 0.5,
                    "raisons": ["Certification AWS"],
                },
            },
            "points_forts": ["Stabilite", "Grands comptes"],
            "points_faibles": ["Trou parcours"],
            "synthese": "Profil senior solide avec bonne experience grands comptes.",
            "classification": "BON",
        }
    )


def _make_response(text: str):
    """Create a mock Gemini response with .text property."""
    response = MagicMock()
    response.text = text
    return response


def _make_response_no_text():
    """Create a mock Gemini response with empty text."""
    response = MagicMock()
    response.text = None
    return response


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestGeminiMatchingServiceInit:
    """Tests for GeminiMatchingService initialization."""

    @patch("app.infrastructure.matching.gemini_matcher.genai")
    def test_client_initialized_with_correct_api_key(self, mock_genai, mock_settings):
        """Test that genai.Client is created with the correct API key."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        service = GeminiMatchingService(mock_settings)
        result = service._get_client()

        mock_genai.Client.assert_called_once_with(api_key="test-api-key-matcher")
        assert result == mock_genai_client

    @patch("app.infrastructure.matching.gemini_matcher.genai")
    def test_client_is_cached(self, mock_genai, mock_settings):
        """Test that _get_client caches the client instance."""
        mock_genai.Client.return_value = MagicMock()

        service = GeminiMatchingService(mock_settings)
        first = service._get_client()
        second = service._get_client()

        assert first is second
        mock_genai.Client.assert_called_once()

    def test_get_client_raises_when_no_api_key(self, mock_settings_no_key):
        """Test that _get_client raises CvMatchingError when API key is missing."""
        service = GeminiMatchingService(mock_settings_no_key)

        with pytest.raises(CvMatchingError, match="[Cc]l.* API|non configur"):
            service._get_client()

    def test_is_configured_true(self, mock_settings):
        """Test _is_configured returns True when API key is set."""
        service = GeminiMatchingService(mock_settings)
        assert service._is_configured() is True

    def test_is_configured_false(self, mock_settings_no_key):
        """Test _is_configured returns False when API key is empty."""
        service = GeminiMatchingService(mock_settings_no_key)
        assert service._is_configured() is False


# ============================================================================
# calculate_match_enhanced Tests
# ============================================================================


class TestCalculateMatchEnhanced:
    """Tests for the calculate_match_enhanced method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_calls_generate_content(
        self, mock_genai, mock_settings, sample_enhanced_response
    ):
        """Test that calculate_match_enhanced calls generate_content with correct model."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_enhanced_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        await service.calculate_match_enhanced(
            cv_text="Senior Python dev with 10 years of experience...",
            job_title_offer="Developpeur Python Senior",
            job_description="Nous recherchons un dev Python...",
            required_skills=["Python", "FastAPI"],
        )

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.5-flash-lite"

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_returns_correct_structure(
        self, mock_genai, mock_settings, sample_enhanced_response
    ):
        """Test that enhanced matching returns properly structured result."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_enhanced_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match_enhanced(
            cv_text="Senior Python dev...",
            job_title_offer="Developpeur Python Senior",
            job_description="Nous recherchons un dev Python...",
        )

        assert result["score_global"] == 72
        assert result["scores_details"]["competences_techniques"] == 80
        assert "Python" in result["competences_matchees"]
        assert "Kubernetes" in result["competences_manquantes"]
        assert result["recommandation"]["niveau"] == "fort"
        # Legacy compatibility fields
        assert result["score"] == 72
        assert isinstance(result["strengths"], list)
        assert isinstance(result["gaps"], list)

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_includes_candidate_info_in_prompt(
        self, mock_genai, mock_settings, sample_enhanced_response
    ):
        """Test that candidate info is included in the prompt."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_enhanced_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        await service.calculate_match_enhanced(
            cv_text="Dev Python...",
            job_title_offer="Dev Python Senior",
            job_description="Mission Python...",
            candidate_job_title="Lead Developer",
            candidate_tjm_range="550-650",
            candidate_availability="2024-03-01",
        )

        call_kwargs = mock_generate.call_args
        prompt = call_kwargs.kwargs["contents"]
        assert "Lead Developer" in prompt
        assert "550-650" in prompt
        assert "2024-03-01" in prompt

    @pytest.mark.asyncio
    async def test_enhanced_match_returns_default_when_not_configured(self, mock_settings_no_key):
        """Test that default result is returned when Gemini is not configured."""
        service = GeminiMatchingService(mock_settings_no_key)
        result = await service.calculate_match_enhanced(
            cv_text="Some CV",
            job_title_offer="Some Job",
            job_description="Some description",
        )

        assert result["score_global"] == 0
        assert result["score"] == 0

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_returns_default_for_empty_inputs(self, mock_genai, mock_settings):
        """Test that default result is returned for empty CV or job description."""
        mock_genai.Client.return_value = MagicMock()

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match_enhanced(
            cv_text="",
            job_title_offer="Dev",
            job_description="Description",
        )

        assert result["score_global"] == 0

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_empty_response_returns_default(self, mock_genai, mock_settings):
        """Test that empty Gemini response returns default result."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response_no_text())
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match_enhanced(
            cv_text="Some CV text",
            job_title_offer="Dev Python",
            job_description="Looking for Python dev...",
        )

        assert result["score_global"] == 0

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_malformed_json_raises_cv_matching_error(
        self, mock_genai, mock_settings
    ):
        """Test that malformed JSON raises CvMatchingError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response("{broken json"))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)

        with pytest.raises(CvMatchingError, match="invalide|echou"):
            await service.calculate_match_enhanced(
                cv_text="Some CV",
                job_title_offer="Dev",
                job_description="Description",
            )

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_api_error_raises_cv_matching_error(
        self, mock_genai, mock_settings
    ):
        """Test that API errors are wrapped in CvMatchingError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(side_effect=RuntimeError("API quota exceeded"))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)

        with pytest.raises(CvMatchingError, match="chou"):
            await service.calculate_match_enhanced(
                cv_text="Some CV",
                job_title_offer="Dev",
                job_description="Description",
            )

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_enhanced_match_score_clamped_to_bounds(self, mock_genai, mock_settings):
        """Test that score_global is clamped between 0 and 100."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = json.dumps(
            {
                "score_global": 150,  # Over the maximum
                "scores_details": {
                    "competences_techniques": 200,
                    "experience": -10,
                    "formation": 50,
                    "soft_skills": 50,
                },
                "competences_matchees": ["Python"],
                "competences_manquantes": [],
                "points_forts": ["Good"],
                "points_vigilance": [],
                "synthese": "Test",
                "recommandation": {"niveau": "fort", "action_suggeree": "Test"},
            }
        )
        mock_generate = AsyncMock(return_value=_make_response(response_data))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match_enhanced(
            cv_text="CV text",
            job_title_offer="Dev",
            job_description="Desc",
        )

        assert result["score_global"] == 100


# ============================================================================
# calculate_match (Legacy) Tests
# ============================================================================


class TestCalculateMatchLegacy:
    """Tests for the legacy calculate_match method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_legacy_match_returns_correct_structure(
        self, mock_genai, mock_settings, sample_legacy_response
    ):
        """Test that legacy matching returns score, strengths, gaps, summary."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_legacy_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match(
            cv_text="Python developer with 5 years experience...",
            job_description="Looking for a Python backend dev...",
        )

        assert result["score"] == 65
        assert "Python" in result["strengths"]
        assert "Cloud experience" in result["gaps"]
        assert "profil backend" in result["summary"]

    @pytest.mark.asyncio
    async def test_legacy_match_returns_default_when_not_configured(self, mock_settings_no_key):
        """Test default result when Gemini is not configured."""
        service = GeminiMatchingService(mock_settings_no_key)
        result = await service.calculate_match("CV text", "Job desc")

        assert result["score"] == 0
        assert result["strengths"] == []
        assert "Analyse non disponible" in result["gaps"]

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_legacy_match_score_clamped_to_bounds(self, mock_genai, mock_settings):
        """Test that score is clamped between 0 and 100."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = json.dumps(
            {
                "score": 250,
                "strengths": [],
                "gaps": [],
                "summary": "Test",
            }
        )
        mock_generate = AsyncMock(return_value=_make_response(response_data))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match("CV text", "Job desc")

        assert result["score"] == 100

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_legacy_match_handles_markdown_wrapped_response(self, mock_genai, mock_settings):
        """Test that markdown-wrapped JSON is parsed correctly."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        raw = '```json\n{"score": 55, "strengths": ["A"], "gaps": ["B"], "summary": "OK"}\n```'
        mock_generate = AsyncMock(return_value=_make_response(raw))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.calculate_match("CV text", "Job desc")

        assert result["score"] == 55


# ============================================================================
# evaluate_cv_quality Tests
# ============================================================================


class TestEvaluateCvQuality:
    """Tests for the evaluate_cv_quality method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_calls_generate_content(
        self, mock_genai, mock_settings, sample_cv_quality_response
    ):
        """Test that evaluate_cv_quality calls generate_content with correct model."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_cv_quality_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        await service.evaluate_cv_quality(cv_text="Senior dev Python 10 ans...")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.5-flash-lite"

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_returns_correct_structure(
        self, mock_genai, mock_settings, sample_cv_quality_response
    ):
        """Test that CV quality evaluation returns correctly structured result."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response(sample_cv_quality_response))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.evaluate_cv_quality(cv_text="Senior dev Python 10 ans...")

        assert result["niveau_experience"] == "SENIOR"
        assert result["annees_experience"] == 10.0
        assert result["note_globale"] == 15.5
        assert result["classification"] == "BON"
        assert "Stabilite" in result["points_forts"]
        assert "details_notes" in result

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_classification_consistent_with_score(
        self, mock_genai, mock_settings
    ):
        """Test that classification is recalculated to be consistent with score."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        # Response says "FAIBLE" but score is 17 which is EXCELLENT
        response_data = json.dumps(
            {
                "niveau_experience": "SENIOR",
                "annees_experience": 12,
                "note_globale": 17,
                "details_notes": {
                    "stabilite_missions": {
                        "note": 7,
                        "max": 8,
                        "duree_moyenne_mois": 30,
                        "commentaire": "Stable",
                    },
                    "qualite_comptes": {
                        "note": 5,
                        "max": 6,
                        "comptes_identifies": ["CAC40"],
                        "commentaire": "Bon",
                    },
                    "parcours_scolaire": {
                        "note": 2,
                        "max": 2,
                        "formations_identifiees": ["Polytechnique"],
                        "commentaire": "Excellent",
                    },
                    "continuite_parcours": {
                        "note": 4,
                        "max": 4,
                        "trous_identifies": [],
                        "commentaire": "Aucun trou",
                    },
                    "bonus_malus": {"valeur": 0.5, "raisons": ["Certification AWS"]},
                },
                "points_forts": ["Solide"],
                "points_faibles": [],
                "synthese": "Excellent profil.",
                "classification": "FAIBLE",  # Deliberately wrong
            }
        )
        mock_generate = AsyncMock(return_value=_make_response(response_data))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.evaluate_cv_quality(cv_text="Expert dev...")

        # Classification should be recalculated based on score 17 >= 16
        assert result["classification"] == "EXCELLENT"

    @pytest.mark.asyncio
    async def test_evaluate_cv_quality_returns_default_when_not_configured(
        self, mock_settings_no_key
    ):
        """Test default result when Gemini is not configured."""
        service = GeminiMatchingService(mock_settings_no_key)
        result = await service.evaluate_cv_quality(cv_text="Some CV text")

        assert result["note_globale"] == 0
        assert result["classification"] == "FAIBLE"

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_returns_default_for_empty_cv(
        self, mock_genai, mock_settings
    ):
        """Test default result when CV text is empty."""
        mock_genai.Client.return_value = MagicMock()

        service = GeminiMatchingService(mock_settings)
        result = await service.evaluate_cv_quality(cv_text="")

        assert result["note_globale"] == 0
        assert result["classification"] == "FAIBLE"

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_empty_response_returns_default(
        self, mock_genai, mock_settings
    ):
        """Test that empty Gemini response returns default result."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response_no_text())
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.evaluate_cv_quality(cv_text="Some CV")

        assert result["note_globale"] == 0

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_malformed_json_raises(self, mock_genai, mock_settings):
        """Test that malformed JSON raises CvMatchingError."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_generate = AsyncMock(return_value=_make_response("{broken"))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)

        with pytest.raises(CvMatchingError, match="invalide|echou"):
            await service.evaluate_cv_quality(cv_text="Some CV")

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_evaluate_cv_quality_note_clamped_to_20(self, mock_genai, mock_settings):
        """Test that note_globale is clamped between 0 and 20."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        response_data = json.dumps(
            {
                "niveau_experience": "SENIOR",
                "annees_experience": 10,
                "note_globale": 25,  # Over max
                "details_notes": {
                    "stabilite_missions": {
                        "note": 8,
                        "max": 8,
                        "duree_moyenne_mois": 36,
                        "commentaire": "OK",
                    },
                    "qualite_comptes": {
                        "note": 6,
                        "max": 6,
                        "comptes_identifies": [],
                        "commentaire": "OK",
                    },
                    "parcours_scolaire": {
                        "note": 2,
                        "max": 2,
                        "formations_identifiees": [],
                        "commentaire": "OK",
                    },
                    "continuite_parcours": {
                        "note": 4,
                        "max": 4,
                        "trous_identifies": [],
                        "commentaire": "OK",
                    },
                    "bonus_malus": {"valeur": 1, "raisons": []},
                },
                "points_forts": [],
                "points_faibles": [],
                "synthese": "Test",
                "classification": "EXCELLENT",
            }
        )
        mock_generate = AsyncMock(return_value=_make_response(response_data))
        mock_genai_client.aio.models.generate_content = mock_generate

        service = GeminiMatchingService(mock_settings)
        result = await service.evaluate_cv_quality(cv_text="Expert dev...")

        assert result["note_globale"] == 20.0


# ============================================================================
# health_check Tests
# ============================================================================


class TestHealthCheck:
    """Tests for the health_check method."""

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_health_check_uses_count_tokens(self, mock_genai, mock_settings):
        """Test that health_check calls count_tokens to verify API connectivity."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_count_tokens = AsyncMock(return_value=MagicMock(total_tokens=1))
        mock_genai_client.aio.models.count_tokens = mock_count_tokens

        service = GeminiMatchingService(mock_settings)
        result = await service.health_check()

        assert result is True
        mock_count_tokens.assert_called_once_with(
            model="gemini-2.5-flash-lite",
            contents="test",
        )

    @pytest.mark.asyncio
    @patch("app.infrastructure.matching.gemini_matcher.genai")
    async def test_health_check_returns_false_on_api_error(self, mock_genai, mock_settings):
        """Test that health_check returns False when API call fails."""
        mock_genai_client = MagicMock()
        mock_genai.Client.return_value = mock_genai_client

        mock_count_tokens = AsyncMock(side_effect=RuntimeError("Invalid API key"))
        mock_genai_client.aio.models.count_tokens = mock_count_tokens

        service = GeminiMatchingService(mock_settings)
        result = await service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_not_configured(self, mock_settings_no_key):
        """Test that health_check returns False when Gemini is not configured."""
        service = GeminiMatchingService(mock_settings_no_key)
        result = await service.health_check()

        assert result is False


# ============================================================================
# Response Parsing Tests
# ============================================================================


class TestResponseParsing:
    """Tests for response parsing helper methods."""

    def test_parse_response_clean_json(self, mock_settings):
        """Test parsing clean JSON response."""
        service = GeminiMatchingService(mock_settings)
        result = service._parse_response(
            '{"score": 75, "strengths": ["A"], "gaps": ["B"], "summary": "OK"}'
        )

        assert result["score"] == 75

    def test_parse_response_markdown_wrapped(self, mock_settings):
        """Test parsing markdown-wrapped JSON."""
        service = GeminiMatchingService(mock_settings)
        result = service._parse_response(
            '```json\n{"score": 60, "strengths": [], "gaps": [], "summary": "T"}\n```'
        )

        assert result["score"] == 60

    def test_parse_response_with_surrounding_text(self, mock_settings):
        """Test parsing JSON from text with extra content."""
        service = GeminiMatchingService(mock_settings)
        result = service._parse_response(
            'Here is: {"score": 42, "strengths": [], "gaps": [], "summary": "S"} done.'
        )

        assert result["score"] == 42

    def test_parse_response_invalid_json_raises(self, mock_settings):
        """Test that invalid JSON raises json.JSONDecodeError."""
        import json

        service = GeminiMatchingService(mock_settings)

        with pytest.raises(json.JSONDecodeError):
            service._parse_response("{not valid json}")

    def test_parse_enhanced_response_with_valid_data(self, mock_settings):
        """Test parsing valid enhanced response."""
        service = GeminiMatchingService(mock_settings)
        result = service._parse_enhanced_response(
            json.dumps(
                {
                    "score_global": 72,
                    "scores_details": {
                        "competences_techniques": 80,
                        "experience": 70,
                        "formation": 60,
                        "soft_skills": 65,
                    },
                    "competences_matchees": ["Python"],
                    "competences_manquantes": ["K8s"],
                    "points_forts": ["Bon dev"],
                    "points_vigilance": [],
                    "synthese": "Profil solide.",
                    "recommandation": {
                        "niveau": "fort",
                        "action_suggeree": "Entretien",
                    },
                }
            )
        )

        assert result["score_global"] == 72
        assert result["score"] == 72  # Legacy compatibility
        assert result["strengths"] == result["points_forts"]


# ============================================================================
# Default Results Tests
# ============================================================================


class TestDefaultResults:
    """Tests for default result methods."""

    def test_default_result_structure(self, mock_settings):
        """Test that _default_result has all required fields."""
        service = GeminiMatchingService(mock_settings)
        result = service._default_result()

        assert "score" in result
        assert "strengths" in result
        assert "gaps" in result
        assert "summary" in result
        assert result["score"] == 0

    def test_default_result_enhanced_structure(self, mock_settings):
        """Test that _default_result_enhanced has all required fields."""
        service = GeminiMatchingService(mock_settings)
        result = service._default_result_enhanced()

        assert result["score_global"] == 0
        assert result["score"] == 0
        assert "scores_details" in result
        assert "recommandation" in result
        # Legacy compatibility
        assert "strengths" in result
        assert "gaps" in result
        assert "summary" in result

    def test_default_cv_quality_result_structure(self, mock_settings):
        """Test that _default_cv_quality_result has all required fields."""
        service = GeminiMatchingService(mock_settings)
        result = service._default_cv_quality_result()

        assert result["note_globale"] == 0
        assert result["classification"] == "FAIBLE"
        assert "details_notes" in result
        assert "stabilite_missions" in result["details_notes"]
        assert "qualite_comptes" in result["details_notes"]
        assert "parcours_scolaire" in result["details_notes"]
        assert "continuite_parcours" in result["details_notes"]
        assert "bonus_malus" in result["details_notes"]


# ============================================================================
# Normalization Tests
# ============================================================================


class TestNormalization:
    """Tests for result normalization methods."""

    def test_normalize_enhanced_result_fills_missing_fields(self, mock_settings):
        """Test that normalization fills missing fields with defaults."""
        service = GeminiMatchingService(mock_settings)
        raw = {"score_global": 50}

        result = service._normalize_enhanced_result(raw)

        assert result["score_global"] == 50
        assert result["scores_details"]["competences_techniques"] == 0
        assert result["scores_details"]["experience"] == 0
        assert result["recommandation"]["niveau"] == "faible"
        assert result["competences_matchees"] == []
        assert result["synthese"] == "Analyse non disponible."

    def test_normalize_enhanced_result_clamps_scores(self, mock_settings):
        """Test that normalization clamps detail scores to 0-100."""
        service = GeminiMatchingService(mock_settings)
        raw = {
            "score_global": 80,
            "scores_details": {
                "competences_techniques": 200,
                "experience": -50,
                "formation": 50,
                "soft_skills": 999,
            },
        }

        result = service._normalize_enhanced_result(raw)

        assert result["scores_details"]["competences_techniques"] == 100
        assert result["scores_details"]["experience"] == 0
        assert result["scores_details"]["soft_skills"] == 100

    def test_normalize_enhanced_result_truncates_lists(self, mock_settings):
        """Test that normalization truncates lists to maximum lengths."""
        service = GeminiMatchingService(mock_settings)
        raw = {
            "score_global": 60,
            "competences_matchees": ["a", "b", "c", "d", "e", "f", "g"],
            "competences_manquantes": ["1", "2", "3", "4", "5", "6", "7"],
            "points_forts": ["x", "y", "z", "w", "v"],
        }

        result = service._normalize_enhanced_result(raw)

        assert len(result["competences_matchees"]) <= 5
        assert len(result["competences_manquantes"]) <= 5
        assert len(result["points_forts"]) <= 3

    def test_normalize_cv_quality_result_fills_missing_fields(self, mock_settings):
        """Test that CV quality normalization fills missing fields."""
        service = GeminiMatchingService(mock_settings)
        raw = {"note_globale": 12}

        result = service._normalize_cv_quality_result(raw)

        assert result["note_globale"] == 12
        assert result["niveau_experience"] == "CONFIRME"
        assert result["details_notes"]["stabilite_missions"]["max"] == 8
        assert result["details_notes"]["qualite_comptes"]["max"] == 6
        assert result["details_notes"]["continuite_parcours"]["max"] == 4

    def test_normalize_cv_quality_result_clamps_values(self, mock_settings):
        """Test that CV quality normalization clamps values to valid ranges."""
        service = GeminiMatchingService(mock_settings)
        raw = {
            "note_globale": 15,
            "details_notes": {
                "stabilite_missions": {"note": 20, "max": 8},  # Over max
                "qualite_comptes": {"note": -5, "max": 6},  # Under min
                "bonus_malus": {"valeur": 5},  # Over max
            },
        }

        result = service._normalize_cv_quality_result(raw)

        assert result["details_notes"]["stabilite_missions"]["note"] == 8
        assert result["details_notes"]["qualite_comptes"]["note"] == 0
        assert result["details_notes"]["bonus_malus"]["valeur"] == 1
