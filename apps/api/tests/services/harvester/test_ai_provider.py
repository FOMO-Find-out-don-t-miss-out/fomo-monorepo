"""Unit tests for the AI provider abstraction and cost controls (FOMO-132, FOMO-137)."""
import json
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


def test_init_client_deepseek_returns_raw_openai_not_instructor() -> None:
    """DeepSeek client must be a raw OpenAI instance, never instructor-wrapped."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    fake_openai = MagicMock(name="raw_openai_client")

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "deepseek"), \
         patch.object(settings, "AI_API_KEY", None), \
         patch.object(settings, "DEEPSEEK_API_KEY", "test-key-for-unit-test"), \
         patch.object(settings, "AI_BASE_URL", "https://api.deepseek.com"), \
         patch.object(settings, "AI_REQUEST_TIMEOUT_SECONDS", 20), \
         patch("openai.OpenAI", return_value=fake_openai) as mock_openai_cls, \
         patch("instructor.from_openai") as mock_instructor:
        result = ai_mod._init_client()

    assert result is fake_openai, "DeepSeek must return the raw OpenAI instance"
    mock_openai_cls.assert_called_once()
    mock_instructor.assert_not_called()


def test_init_client_gemini_no_key_returns_none() -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    with patch.object(settings, "AI_EXTRACTION_ENABLED", True), \
         patch.object(settings, "AI_PROVIDER", "gemini"), \
         patch.object(settings, "GOOGLE_API_KEY", None):
        result = ai_mod._init_client()
    assert result is None


# ---------------------------------------------------------------------------
# AiExtractor.extract() — shared behaviour
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
async def test_provider_error_returns_empty_list() -> None:
    """Any exception from the underlying client returns []."""
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
    # The user message contains the truncated text plus prompt header.
    # The raw text portion was capped at 200; total message length is well under 1000.
    assert len(captured[0]) < 1000


# ---------------------------------------------------------------------------
# DeepSeek JSON Output path (FOMO-137)
# ---------------------------------------------------------------------------

# Minimum 50 chars of body text are required before extract() calls the provider.
_LONG_HTML = (
    "<html><body>"
    "Jazz Night Live at the Blue Note Club in Athens this Saturday evening at 21:00. "
    "Tickets available at the door. Doors open 20:00."
    "</body></html>"
)


def _make_deepseek_response(json_str: str) -> MagicMock:
    """Build a mock that looks like a raw OpenAI chat completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = json_str
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.mark.asyncio
async def test_deepseek_request_uses_json_object_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek path must set response_format={"type":"json_object"}."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    await ai_mod.AiExtractor.extract(
        _LONG_HTML,
        country_hint="GR",
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_deepseek_request_disables_thinking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek path must pass extra_body={"thinking":{"type":"disabled"}}."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("extra_body") == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_deepseek_request_omits_tools_and_tool_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek path must NOT pass tools or tool_choice to the API."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "tools" not in call_kwargs, "DeepSeek must not pass 'tools'"
    assert "tool_choice" not in call_kwargs, "DeepSeek must not pass 'tool_choice'"


@pytest.mark.asyncio
async def test_deepseek_request_omits_response_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek path must NOT pass response_model (instructor parameter)."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "response_model" not in call_kwargs, (
        "DeepSeek must not pass instructor's 'response_model'"
    )


@pytest.mark.asyncio
async def test_deepseek_valid_json_response_returns_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek JSON response with one event produces one ExtractedEvent."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    json_body = json.dumps({
        "events": [{
            "title": "Jazz Night",
            "start_time": "2026-06-15T21:00:00",
            "location_name": "Blue Note Athens",
            "country_code": "GR",
            "category": "music",
            "sub_category": "jazz",
            "tags": ["jazz"],
        }]
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response(json_body)

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    results = await ai_mod.AiExtractor.extract(
        "<html><body>Jazz Night Live at Blue Note Athens on June 15 at 9pm.</body></html>",
        country_hint="GR",
        source_domain="test.com",
    )

    assert len(results) == 1
    assert results[0].title == "Jazz Night"
    assert results[0].location_name == "Blue Note Athens"
    assert results[0].source_provider == "test.com"
    assert results[0].ingestion_method == "html_fallback"


@pytest.mark.asyncio
async def test_deepseek_malformed_json_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON from DeepSeek returns [] without raising."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response(
        "Sorry, I cannot extract any events from this text."
    )

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    results = await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )
    assert results == []


@pytest.mark.asyncio
async def test_deepseek_empty_events_array_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """{"events": []} from DeepSeek returns []."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    results = await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )
    assert results == []


@pytest.mark.asyncio
async def test_deepseek_provider_exception_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek client exception returns [] without raising."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("DeepSeek 503")

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    results = await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )
    assert results == []


@pytest.mark.asyncio
async def test_deepseek_prompt_contains_json_keyword(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DeepSeek request messages must include the word 'json' (required by JSON Output mode)."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    from app.core.config import settings

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_deepseek_response('{"events": []}')

    monkeypatch.setattr(ai_mod, "_client", mock_client)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")

    await ai_mod.AiExtractor.extract(
        _LONG_HTML,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    all_message_text = " ".join(
        m["content"] for m in call_kwargs.get("messages", []) if isinstance(m, dict)
    )
    assert "json" in all_message_text.lower(), (
        "DeepSeek JSON Output mode requires the word 'json' in the prompt"
    )


# ---------------------------------------------------------------------------
# _parse_deepseek_response unit tests
# ---------------------------------------------------------------------------


def test_parse_deepseek_response_valid() -> None:
    raw = json.dumps({
        "events": [{"title": "Gig", "start_time": "2026-06-01T20:00:00"}]
    })
    result = AiExtractor._parse_deepseek_response(raw, "test.com")
    assert len(result) == 1
    assert result[0].title == "Gig"
    assert result[0].source_provider == "test.com"
    assert result[0].ingestion_method == "html_fallback"


def test_parse_deepseek_response_none_returns_empty() -> None:
    result = AiExtractor._parse_deepseek_response(None, "test.com")
    assert result == []


def test_parse_deepseek_response_bad_json_returns_empty() -> None:
    result = AiExtractor._parse_deepseek_response("{not valid json{{", "test.com")
    assert result == []


def test_parse_deepseek_response_events_not_list_returns_empty() -> None:
    raw = json.dumps({"events": "should be a list"})
    result = AiExtractor._parse_deepseek_response(raw, "test.com")
    assert result == []


def test_parse_deepseek_response_extra_fields_tolerated() -> None:
    """Unknown fields from DeepSeek (e.g. city, source_url) are silently ignored."""
    raw = json.dumps({
        "events": [{
            "title": "Beach Party",
            "start_time": "2026-08-01T18:00:00",
            "city": "Mykonos",
            "source_url": "https://example.com/event",
            "unknown_future_field": 42,
        }]
    })
    result = AiExtractor._parse_deepseek_response(raw, None)
    assert len(result) == 1
    assert result[0].title == "Beach Party"


def test_parse_deepseek_response_skips_malformed_items() -> None:
    """Items with missing required fields are skipped; valid items are returned."""
    raw = json.dumps({
        "events": [
            {"title": "Good Event", "start_time": "2026-09-01T19:00:00"},
            "not a dict",
            {"no_title_field": True},
        ]
    })
    # "Good Event" is valid; "not a dict" is skipped; missing title causes validation error
    result = AiExtractor._parse_deepseek_response(raw, None)
    # At minimum "Good Event" should parse; item without title may or may not depending
    # on Pydantic defaults — the key behaviour is no exception is raised.
    assert isinstance(result, list)
    titles = [ev.title for ev in result]
    assert "Good Event" in titles


# ---------------------------------------------------------------------------
# FOMO-131 guard regression
# ---------------------------------------------------------------------------


def test_fomo131_guard_still_active() -> None:
    """FOMO-131 autouse guard is still enforced (regression check)."""
    import app.services.harvester.cleansing.ai_extractor as ai_mod

    with pytest.raises(RuntimeError, match="External AI call attempted"):
        ai_mod._client.chat.completions.create()


# Keep the name in scope for the _parse_deepseek_response direct tests above.
from app.services.harvester.cleansing.ai_extractor import AiExtractor  # noqa: E402
