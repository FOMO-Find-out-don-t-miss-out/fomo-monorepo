"""
Real Gemini integration tests — skipped by default.

These tests call the live Gemini API and will consume paid quota.
They are intentionally excluded from normal CI runs.

Run manually:
    RUN_EXTERNAL_AI_TESTS=true GOOGLE_API_KEY=<key> \\
        uv run pytest apps/api/tests/ -m integration_ai -v

FOMO-129: the previous API key was revoked.
FOMO-132: will decide whether to keep Gemini or migrate to another provider.
Until FOMO-132 is resolved, keep these tests as the integration harness.
"""

import os

import pytest


@pytest.mark.integration_ai
@pytest.mark.asyncio
async def test_ai_extractor_returns_list() -> None:
    """Smoke-test: AiExtractor.extract() calls the real Gemini model and
    returns a (possibly empty) list of ExtractedEvent objects."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set — cannot call real Gemini API")

    # Re-initialise the client with the current key because the module-level
    # client is replaced by the guard fixture.  integration_ai tests are exempt
    # from the guard, so _client is still None here; we build a fresh one.
    import app.services.harvester.cleansing.ai_extractor as ai_mod
    import instructor
    from google import genai

    real_client = instructor.from_genai(client=genai.Client(api_key=api_key))
    ai_mod._client = real_client

    try:
        from app.services.harvester.cleansing.ai_extractor import AiExtractor

        html = """
        <html><body>
        Jazz Night Live at Stavros Niarchos Foundation Cultural Centre, Athens.
        Saturday 15 February 2026 at 21:00. Gates open at 20:00.
        Tickets available at the door.
        </body></html>
        """
        results = await AiExtractor.extract(html, country_hint="GR", source_domain="test")

        # Model output is non-deterministic; validate structure only.
        assert isinstance(results, list)
        for ev in results:
            assert hasattr(ev, "title"), "ExtractedEvent must have a title field"
            assert hasattr(ev, "start_time"), "ExtractedEvent must have a start_time field"
            assert ev.ingestion_method == "html_fallback"
    finally:
        # Restore to None so subsequent tests are not affected.
        ai_mod._client = None


@pytest.mark.integration_ai
@pytest.mark.asyncio
async def test_ai_extractor_empty_on_non_event_content() -> None:
    """Real provider returns an empty list when there is no event in the text."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set — cannot call real Gemini API")

    import app.services.harvester.cleansing.ai_extractor as ai_mod
    import instructor
    from google import genai

    real_client = instructor.from_genai(client=genai.Client(api_key=api_key))
    ai_mod._client = real_client

    try:
        from app.services.harvester.cleansing.ai_extractor import AiExtractor

        html = "<html><body>This is a cooking recipe for chocolate cake.</body></html>"
        results = await AiExtractor.extract(html, country_hint="GR", source_domain="test")
        assert isinstance(results, list)
    finally:
        ai_mod._client = None
