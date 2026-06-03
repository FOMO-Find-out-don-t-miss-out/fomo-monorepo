# FOMO API

FastAPI backend for the FOMO platform.

---

## Running tests

### Normal test run (zero cost, no credentials required)

```bash
uv run pytest apps/api/tests/
```

All external AI provider calls are blocked by a safety guard in `tests/conftest.py`.
No API key of any kind is needed for normal test runs.

```bash
# Equivalent — explicitly exclude the integration_ai marker:
uv run pytest apps/api/tests/ -m "not integration_ai"

# Confirm no Google/DeepSeek credentials are required:
unset GOOGLE_API_KEY AI_API_KEY && uv run pytest apps/api/tests/
```

### AI provider integration tests (opt-in, paid quota)

Tests marked `@pytest.mark.integration_ai` call the live AI API and are
**skipped by default**.

DeepSeek (recommended for staging/MVP):

```bash
RUN_EXTERNAL_AI_TESTS=true AI_PROVIDER=deepseek AI_API_KEY=<your-key> \
    uv run pytest apps/api/tests/ -m integration_ai -v
```

Gemini (legacy):

```bash
RUN_EXTERNAL_AI_TESTS=true AI_PROVIDER=gemini GOOGLE_API_KEY=<your-key> \
    uv run pytest apps/api/tests/ -m integration_ai -v
```

CI never sets `RUN_EXTERNAL_AI_TESTS`, so these tests never run in CI.

---

## AI provider configuration

### Default (local / dev / CI)

AI extraction is **disabled by default** — no API key is needed and no external call is made.

```
AI_EXTRACTION_ENABLED=false
AI_PROVIDER=disabled
```

### Staging / MVP — DeepSeek

```
AI_EXTRACTION_ENABLED=true
AI_PROVIDER=deepseek
AI_API_KEY=<your-deepseek-api-key>    # or DEEPSEEK_API_KEY=...
AI_MODEL=deepseek-chat
AI_BASE_URL=https://api.deepseek.com
```

DeepSeek uses an OpenAI-compatible API. The client is initialized via
`openai.OpenAI(base_url=..., api_key=...)` wrapped with `instructor`.

### Legacy — Gemini

Set `AI_PROVIDER=gemini` and supply `GOOGLE_API_KEY`. Gemini is **not required**
for local/dev/CI; it is kept as a fallback path only.

### Cost controls

| Setting | Default | Purpose |
|---|---|---|
| `AI_MAX_INPUT_CHARS` | 12000 | Truncates cleaned HTML text before sending to model |
| `AI_MAX_OUTPUT_TOKENS` | 800 | Caps model output length |
| `AI_REQUEST_TIMEOUT_SECONDS` | 20 | HTTP timeout for provider calls |

---

## AI safety guard (FOMO-131)

`tests/conftest.py` installs an autouse fixture `_block_real_ai_client` for
every normal test. It replaces `ai_extractor._client` with a sentinel that
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
