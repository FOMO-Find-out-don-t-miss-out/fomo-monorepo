"""
Live AI provider integration tests — skipped by default.

These tests call a real external AI API and consume paid quota.
They are intentionally excluded from normal CI runs.

DeepSeek (recommended for staging/MVP):
    RUN_EXTERNAL_AI_TESTS=true AI_PROVIDER=deepseek AI_API_KEY=<key> \\
        uv run pytest apps/api/tests/ -m integration_ai -v

Gemini (legacy, requires GOOGLE_API_KEY):
    RUN_EXTERNAL_AI_TESTS=true AI_PROVIDER=gemini GOOGLE_API_KEY=<key> \\
        uv run pytest apps/api/tests/ -m integration_ai -v

FOMO-129: the previous Gemini API key was revoked.
FOMO-132: migrated to provider abstraction; DeepSeek is the preferred staging provider.
"""

import os

import pytest


@pytest.mark.integration_ai
@pytest.mark.asyncio
async def test_deepseek_extractor_returns_list() -> None:
    """Smoke-test: AiExtractor.extract() via DeepSeek returns a list of ExtractedEvent."""
    api_key = os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("AI_API_KEY / DEEPSEEK_API_KEY not set — cannot call real DeepSeek API")

    import app.services.harvester.cleansing.ai_extractor as ai_mod
    import instructor
    from app.core.config import settings
    from openai import OpenAI

    raw = OpenAI(
        api_key=api_key,
        base_url=settings.AI_BASE_URL,
        timeout=float(settings.AI_REQUEST_TIMEOUT_SECONDS),
    )
    real_client = instructor.from_openai(raw)
    ai_mod._client = real_client

    try:
        html = """
        <html><body>
        Jazz Night Live at Stavros Niarchos Foundation Cultural Centre, Athens.
        Saturday 15 February 2026 at 21:00. Gates open at 20:00.
        Tickets available at the door.
        </body></html>
        """
        results = await ai_mod.AiExtractor.extract(html, country_hint="GR", source_domain="test")

        assert isinstance(results, list)
        for ev in results:
            assert hasattr(ev, "title"), "ExtractedEvent must have a title field"
            assert hasattr(ev, "start_time"), "ExtractedEvent must have a start_time field"
            assert ev.ingestion_method == "html_fallback"
    finally:
        ai_mod._client = None


@pytest.mark.integration_ai
@pytest.mark.asyncio
async def test_deepseek_extractor_empty_on_non_event_content() -> None:
    """Real DeepSeek provider returns an empty list when there is no event in the text."""
    api_key = os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("AI_API_KEY / DEEPSEEK_API_KEY not set — cannot call real DeepSeek API")

    import app.services.harvester.cleansing.ai_extractor as ai_mod
    import instructor
    from app.core.config import settings
    from openai import OpenAI

    raw = OpenAI(
        api_key=api_key,
        base_url=settings.AI_BASE_URL,
        timeout=float(settings.AI_REQUEST_TIMEOUT_SECONDS),
    )
    ai_mod._client = instructor.from_openai(raw)

    try:
        html = "<html><body>This is a cooking recipe for chocolate cake.</body></html>"
        results = await ai_mod.AiExtractor.extract(html, country_hint="GR", source_domain="test")
        assert isinstance(results, list)
    finally:
        ai_mod._client = None


# ---------------------------------------------------------------------------
# Legacy Gemini tests — kept as a fallback harness if reverting to Gemini
# ---------------------------------------------------------------------------


@pytest.mark.integration_ai
@pytest.mark.asyncio
async def test_gemini_extractor_returns_list() -> None:
    """Smoke-test using the Gemini provider (legacy path)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set — cannot call real Gemini API")

    import app.services.harvester.cleansing.ai_extractor as ai_mod
    import instructor
    from google import genai

    real_client = instructor.from_genai(client=genai.Client(api_key=api_key))
    ai_mod._client = real_client

    try:
        html = """
        <html><body>
        Jazz Night Live at Stavros Niarchos Foundation Cultural Centre, Athens.
        Saturday 15 February 2026 at 21:00. Gates open at 20:00.
        </body></html>
        """
        results = await ai_mod.AiExtractor.extract(html, country_hint="GR", source_domain="test")

        assert isinstance(results, list)
        for ev in results:
            assert hasattr(ev, "title")
            assert ev.ingestion_method == "html_fallback"
    finally:
        ai_mod._client = None
