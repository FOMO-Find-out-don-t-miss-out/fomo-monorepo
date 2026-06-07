# FOMO API

FastAPI backend for the FOMO platform.

---

## Local environment setup

```bash
cp apps/api/.env.example apps/api/.env.local
# Edit apps/api/.env.local with your local values
```

`.env` and `.env.local` are git-ignored. Never commit files containing real credentials.
In Docker Compose the vars in the root `.env` are injected automatically — `apps/api/.env.local`
is only needed when running the API process directly (outside Docker).

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

### Staging / MVP — DeepSeek (FOMO-137: JSON Output mode)

```
AI_EXTRACTION_ENABLED=true
AI_PROVIDER=deepseek
AI_API_KEY=<your-deepseek-api-key>    # or DEEPSEEK_API_KEY=...
AI_MODEL=deepseek-v4-flash
AI_BASE_URL=https://api.deepseek.com
```

DeepSeek uses a **raw** `openai.OpenAI` client (not instructor-wrapped) and the
[JSON Output mode](https://api-docs.deepseek.com/guides/json_mode):

- `response_format={"type": "json_object"}` — structured JSON without tool calls.
- `extra_body={"thinking": {"type": "disabled"}}` — disables thinking mode, which
  does not support `tool_choice` parameters.
- No `tools`, no `tool_choice`, no `response_model` are passed.
- The prompt explicitly contains the word "json" and a compact schema example,
  as required by DeepSeek's JSON Output mode.

The response is parsed from `choices[0].message.content` and validated into
`ExtractedEvent` objects. Malformed JSON or provider errors return `[]`.

### Legacy — Gemini

Set `AI_PROVIDER=gemini` and supply `GOOGLE_API_KEY`. Gemini uses the
`instructor` structured-output path and is kept as a fallback only.

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

Tests that mock the **DeepSeek** path must return a response shaped like a raw
OpenAI completion (with `choices[0].message.content` as a JSON string):

```python
import json
from unittest.mock import MagicMock, patch

json_body = json.dumps({"events": [{"title": "Test Event", "start_time": "2026-01-01T00:00:00"}]})
mock_choice = MagicMock()
mock_choice.message.content = json_body
mock_response = MagicMock()
mock_response.choices = [mock_choice]

with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client, \
     patch.object(settings, "AI_PROVIDER", "deepseek"):
    mock_client.chat.completions.create.return_value = mock_response
    result = await AiExtractor.extract(html)
```

Tests that mock the **Gemini / instructor** path use the `response.tasks` shape:

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

## Running tests

### Normal test run (zero cost, no credentials required)

```bash
uv run pytest apps/api/tests/
```

All external AI provider calls are blocked by the safety guard in `tests/conftest.py`.
No API key of any kind is needed for normal test runs.

```bash
# Explicitly exclude the integration_ai marker:
uv run pytest apps/api/tests/ -m "not integration_ai"

# Confirm no credentials are required:
unset GOOGLE_API_KEY AI_API_KEY && uv run pytest apps/api/tests/
```

### AI provider integration tests (opt-in, paid quota)

Tests marked `@pytest.mark.integration_ai` call the live AI API and are
**skipped by default**.

DeepSeek (JSON Output mode — recommended for staging/MVP):

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

## Staging smoke test

Run a one-off manual extraction against the live staging API pod to verify
end-to-end DeepSeek connectivity:

```bash
kubectl exec -n fomo-staging deploy/fomo-api -- sh -c 'PYTHONPATH=/app:/app/apps/api python - <<PY
import asyncio
from app.services.harvester.cleansing.ai_extractor import AiExtractor

html = """
<html>
  <body>
    <h1>Test Jazz Night Athens</h1>
    <p>Date: 2026-07-10 21:00</p>
    <p>Location: Technopolis City of Athens</p>
    <p>A live jazz music event in Athens.</p>
  </body>
</html>
"""

async def main():
    events = await AiExtractor.extract(
        html,
        country_hint="GR",
        source_domain="manual-staging-smoke-test",
    )
    print("events_count=" + str(len(events)))
    for event in events:
        print("title=" + str(getattr(event, "title", None)))
        print("location_name=" + str(getattr(event, "location_name", None)))

asyncio.run(main())
PY'
```

Expected output when DeepSeek is reachable and extraction succeeds:

```
events_count=1
title=Test Jazz Night Athens
location_name=Technopolis City of Athens
```

---

## Database migrations

```bash
docker compose exec api alembic -c apps/api/alembic.ini revision --autogenerate -m "description"
docker compose exec api alembic -c apps/api/alembic.ini upgrade head
```
