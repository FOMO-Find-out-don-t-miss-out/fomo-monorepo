# FOMO API

FastAPI backend for the FOMO platform.

---

## Running tests

### Normal test run (zero cost, no credentials required)

```bash
uv run pytest apps/api/tests/
```

All external AI provider calls are blocked by a safety guard in `tests/conftest.py`.
No `GOOGLE_API_KEY` or any other paid API credential is needed.

```bash
# Equivalent — explicitly exclude the integration_ai marker:
uv run pytest apps/api/tests/ -m "not integration_ai"

# Without any Google credentials in the environment:
unset GOOGLE_API_KEY && uv run pytest apps/api/tests/
```

### AI provider integration tests (opt-in, paid quota)

Tests marked `@pytest.mark.integration_ai` call the live Gemini API and are
**skipped by default**.  Run them manually when you have a valid key:

```bash
RUN_EXTERNAL_AI_TESTS=true GOOGLE_API_KEY=<your-key> \
    uv run pytest apps/api/tests/ -m integration_ai -v
```

CI never sets `RUN_EXTERNAL_AI_TESTS`, so these tests never run in CI.

> **FOMO-129**: the previous Gemini API key was revoked.  
> **FOMO-132**: will decide whether to keep Gemini or migrate to another AI provider.  
> Until FOMO-132 is resolved, do not add new real-API test coverage.

---

## AI safety guard

`tests/conftest.py` installs an autouse fixture `_block_real_ai_client` for
every normal test.  It replaces `ai_extractor._client` with a sentinel that
raises `RuntimeError` if `chat.completions.create()` is called without an
explicit test-level mock:

```
RuntimeError: External AI call attempted during tests.
Patch app.services.harvester.cleansing.ai_extractor._client with a mock,
or opt in with @pytest.mark.integration_ai + RUN_EXTERNAL_AI_TESTS=true.
```

Tests that need AI extraction output must supply their own mock:

```python
from unittest.mock import MagicMock, patch
from packages.domain.schemas.extracted_event import ExtractedEvent

mock_event = ExtractedEvent(title="Test Event", start_time="2026-01-01T00:00:00Z")
mock_response = MagicMock()
mock_response.tasks = [mock_event]

with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
    mock_client.chat.completions.create.return_value = mock_response
    result = await CleansingService.clean_html_fallback(html)
```

---

## Database migrations

```bash
docker compose exec api alembic -c apps/api/alembic.ini revision --autogenerate -m "description"
docker compose exec api alembic -c apps/api/alembic.ini upgrade head
```
