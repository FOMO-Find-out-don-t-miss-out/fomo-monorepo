"""Unit tests for the AI provider abstraction and cost controls (FOMO-132)."""
from unittest.mock import MagicMock, patch

import pytest

from packages.domain.schemas.extracted_event import (
    ExtractedEvent,
)

# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


def test_default_config_ai_disabled() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["AI_EXTRACTION_ENABLED"].default is False
    assert Settings.model_fields["AI_PROVIDER"].default == "disabled"


def test_default_ai_model_is_set() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["AI_MODEL"].default is not None


def test_no_google_api_key_required() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["GOOGLE_API_KEY"].default is None


def test_no_ai_api_key_required_by_default() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["AI_API_KEY"].default is None


def test_cost_control_defaults() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["AI_MAX_INPUT_CHARS"].default == 12000
    assert Settings.model_fields["AI_MAX_OUTPUT_TOKENS"].default == 800
    assert Settings.model_fields["AI_REQUEST_TIMEOUT_SECONDS"].default == 20


# ---------------------------------------------------------------------------
# _init_client logic
# ---------------------------------------------------------------------------


def test_init_client_disabled_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", False):
        result = ai_mod._init_client()
    assert result is None


def test_init_client_provider_disabled_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "disabled"):
        result = ai_mod._init_client()
    assert result is None


def test_init_client_deepseek_no_key_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "deepseek"), \
         patch.object(settings, "AI_API_KEY", None), \
         patch.object(settings, "DEEPSEEK_API_KEY", None):
        result = ai_mod._init_client()
    assert result is None


def test_init_client_unknown_provider_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "unknown_llm"):
        result = ai_mod._init_client()
    assert result is None


def test_init_client_deepseek_uses_deepseek_api_key_alias() -> None:
    """DEEPSEEK_API_KEY is accepted when AI_API_KEY is absent."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    fake_instructor = MagicMock()
    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "deepseek"), \
         patch.object(settings, "AI_API_KEY", None), \
         patch.object(settings, "DEEPSEEK_API_KEY", "sk-fake"), \
         patch.object(settings, "AI_BASE_URL", "https://api.deepseek.com"), \
         patch.object(settings, "AI_REQUEST_TIMEOUT_SECONDS", 20), \
         patch("instructor.from_openai", return_value=fake_instructor), \
         patch("openai.OpenAI"):
        result = ai_mod._init_client()
    assert result is fake_instructor


def test_init_client_gemini_no_key_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "gemini"), \
         patch.object(settings, "GOOGLE_API_KEY", None):
        result = ai_mod._init_client()
    assert result is None


# ---------------------------------------------------------------------------
# AiExtractor.extract() behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_returns_empty_when_client_none(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod

    monkeypatch.setattr(ai_mod, "_client", None)
    result = await ai_mod.AiExtractor.extract(
        "<html><body>Long enough text to pass the fifty character minimum</body></html>"
    )
    assert result == []


@pytest.mark.asyncio
async def test_extract_returns_empty_on_short_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod

    mock_client = MagicMock()
    monkeypatch.setattr(ai_mod, "_client", mock_client)
    result = await ai_mod.AiExtractor.extract("<html><body>short</body></html>")
    assert result == []
    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_mocked_deepseek_response_parses_correctly() -> None:
    mock_event = ExtractedEvent(
        title="Jazz Night",
        start_time="2026-06-15T21:00:00Z",
        location_name="Blue Note Athens",
        city_hint="Athens",
    )
    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        import app.services.harvester.cleansing.ai_extractor as ai_mod

        html = "<html><body>Jazz Night Live at Blue Note Athens on June 15 at 9pm.</body></html>"
        results = await ai_mod.AiExtractor.extract(
            html, country_hint="GR", source_domain="test.com"
        )

    assert len(results) == 1
    assert results[0].title == "Jazz Night"
    assert results[0].location_name == "Blue Note Athens"
    assert results[0].source_provider == "test.com"
    assert results[0].ingestion_method == "html_fallback"


@pytest.mark.asyncio
async def test_provider_error_returns_empty_list() -> None:
    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("API timeout")
        import app.services.harvester.cleansing.ai_extractor as ai_mod

        result = await ai_mod.AiExtractor.extract(
            "<html><body>Long enough text to pass the fifty character minimum.</body></html>"
        )
    assert result == []


@pytest.mark.asyncio
async def test_input_truncated_to_max_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """The text sent to the model must not exceed AI_MAX_INPUT_CHARS."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_event = ExtractedEvent(title="T", start_time="2026-01-01T00:00:00Z")
    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    captured: list[str] = []

    def capture_create(**kwargs: object) -> MagicMock:
        for msg in kwargs.get("messages", []):  # type: ignore[union-attr]
            if isinstance(msg, dict) and msg.get("role") == "user":
                captured.append(str(msg["content"]))
        return mock_response

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = capture_create

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_MAX_INPUT_CHARS", 200)

    long_body = "Event at a venue. " * 500  # ~9 500 chars of clean text
    html = f"<html><body>{long_body}</body></html>"
    await ai_mod.AiExtractor.extract(html)

    assert len(captured) == 1
    # The user message contains the truncated text plus prompt header (~200 chars of boilerplate).
    # The raw text portion was capped at 200; total message length should be well under 1000.
    assert len(captured[0]) < 1000


# ---------------------------------------------------------------------------
# FOMO-131 guard regression
# ---------------------------------------------------------------------------


def test_fomo131_guard_still_active() -> None:
    """FOMO-131 autouse guard is still enforced (regression check)."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod

    with pytest.raises(RuntimeError, match="External AI call attempted"):
        ai_mod._client.chat.completions.create()
