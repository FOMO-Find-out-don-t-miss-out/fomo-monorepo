import json
import logging
import re
from typing import Any

import instructor
from app.core.config import settings
from bs4 import BeautifulSoup

from packages.domain.schemas.extracted_event import ExtractedEvent, IterableExtractedEvent

logger = logging.getLogger(__name__)

# _client holds the active API client, or None when disabled.
#
# Provider mapping:
#   deepseek -> raw openai.OpenAI instance  (JSON Output mode; no instructor)
#   gemini   -> instructor-wrapped genai client
#
# The FOMO-131 test guard (conftest.py) replaces this with a sentinel that
# raises RuntimeError on any .chat.completions.create() call, preventing
# accidental paid API hits during normal tests.
_client: Any = None


def _init_client() -> Any:  # noqa: ANN401
    """Return a provider-appropriate client based on current settings, or None.

    DeepSeek returns a raw openai.OpenAI instance.
    Gemini returns an instructor-patched client.
    All other cases return None.
    """
    if not settings.AI_EXTRACTION_ENABLED or settings.AI_PROVIDER == "disabled":
        logger.debug("AI extraction disabled (AI_PROVIDER=%s).", settings.AI_PROVIDER)
        return None

    if settings.AI_PROVIDER == "deepseek":
        api_key = settings.AI_API_KEY or settings.DEEPSEEK_API_KEY
        if not api_key:
            logger.warning(
                "AI_PROVIDER=deepseek but neither AI_API_KEY nor DEEPSEEK_API_KEY is set."
                " AI extraction disabled."
            )
            return None
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url=settings.AI_BASE_URL,
                timeout=float(settings.AI_REQUEST_TIMEOUT_SECONDS),
            )
            logger.info(
                "DeepSeek AI client initialized (model=%s, JSON Output mode).",
                settings.AI_MODEL,
            )
            return client  # raw client — NOT instructor-wrapped
        except Exception as exc:
            logger.error("Failed to initialize DeepSeek client: %s", exc)
            return None

    if settings.AI_PROVIDER == "gemini":
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            logger.warning(
                "AI_PROVIDER=gemini but GOOGLE_API_KEY is not set. AI extraction disabled."
            )
            return None
        try:
            from google import genai

            raw = genai.Client(api_key=api_key)
            logger.info("Gemini AI client initialized (model=%s).", settings.AI_MODEL)
            return instructor.from_genai(client=raw)
        except Exception as exc:
            logger.error("Failed to initialize Gemini client: %s", exc)
            return None

    logger.warning("Unknown AI_PROVIDER=%r. AI extraction disabled.", settings.AI_PROVIDER)
    return None


_client = _init_client()

_GLOBAL_TAGS = [
    "Concert", "Festival", "Clubbing", "DJ Set", "Live Music",
    "Pop", "Electronic", "Hip-Hop", "Rock", "Jazz", "Classical",
    "Art", "Workshop", "Conference", "Outdoor",
]

# Instructor-based system prompt (Gemini / other instructor-compatible providers).
_SYSTEM_PROMPT = (
    "You are a professional event data extractor.\n"
    "Return ONLY valid JSON. No explanations.\n\n"
    "Extraction Rules:\n"
    "1. Extract ONLY: Title, Start Time, End Time, and Venue details.\n"
    "2. DO NOT extract descriptions or image URLs under any circumstances.\n"
    "3. Strict Classification Hierarchy: Venue blindness, "
    "forbid 'Other' if musical keywords are present."
)

# Compact JSON example embedded in the DeepSeek user prompt.
# DeepSeek JSON Output mode requires the word "json" in the prompt and a
# concrete schema example so the model knows the expected output shape.
_DEEPSEEK_JSON_EXAMPLE = (
    '{"events": ['
    '{"title": "Test Jazz Night Athens",'
    ' "start_time": "2026-07-10T21:00:00",'
    ' "end_time": null,'
    ' "location_name": "Technopolis City of Athens",'
    ' "search_term": "Technopolis City of Athens Athens GR",'
    ' "country_code": "GR",'
    ' "category": "music",'
    ' "sub_category": "jazz",'
    ' "tags": ["jazz", "live music"]}'
    "]}"
)


class AiExtractor:
    """Extracts structured event data from unstructured HTML using the configured LLM."""

    @staticmethod
    def _strip_html_noise(html_text: str) -> str:
        """Strip scripts, styles, nav/footer/header elements and collapse whitespace."""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    async def extract(
        cls,
        html_text: str,
        country_hint: str | None = None,
        source_domain: str | None = None,
    ) -> list[ExtractedEvent]:
        """Strip noise from HTML and call the configured LLM to extract event data.

        Routes internally by AI_PROVIDER:
          - deepseek: JSON Output mode via raw OpenAI client (no instructor, no tool_choice)
          - gemini / other instructor-compatible: instructor structured-output path
        """
        if not _client:
            logger.debug("AI client not configured. Skipping extraction.")
            return []

        cleaned_text = cls._strip_html_noise(html_text)
        if len(cleaned_text) < 50:
            return []

        # Cost control: cap input to configured limit before sending to the model.
        if len(cleaned_text) > settings.AI_MAX_INPUT_CHARS:
            logger.debug(
                "AI input truncated %d -> %d chars.",
                len(cleaned_text),
                settings.AI_MAX_INPUT_CHARS,
            )
            cleaned_text = cleaned_text[: settings.AI_MAX_INPUT_CHARS]

        logger.debug(
            "AI extraction: provider=%s model=%s input_chars=%d",
            settings.AI_PROVIDER,
            settings.AI_MODEL,
            len(cleaned_text),
        )

        if settings.AI_PROVIDER == "deepseek":
            return cls._extract_deepseek(cleaned_text, country_hint, source_domain)

        return cls._extract_instructor(cleaned_text, country_hint, source_domain)

    # ------------------------------------------------------------------
    # DeepSeek: JSON Output mode
    # ------------------------------------------------------------------

    @classmethod
    def _extract_deepseek(
        cls,
        cleaned_text: str,
        country_hint: str | None,
        source_domain: str | None,
    ) -> list[ExtractedEvent]:
        """Call DeepSeek using JSON Output mode.

        Uses response_format={"type":"json_object"} and disables thinking mode
        via extra_body so the model never receives tool_choice parameters.
        """
        system_prompt = (
            "You are a professional event data extractor. "
            "Return ONLY valid json with no explanations, no markdown, and no code blocks. "
            "Your entire response must be a JSON object with an 'events' array."
        )
        user_prompt = (
            "Extract event details from the following text and return a JSON object.\n"
            f"Context country: {country_hint or 'Global'}.\n\n"
            "Return a JSON object with this exact structure (example):\n"
            f"{_DEEPSEEK_JSON_EXAMPLE}\n\n"
            'If there are no events in the text, return: {"events": []}\n\n'
            "Fields to extract:\n"
            "- title: event name (required)\n"
            "- start_time: ISO 8601 datetime\n"
            "- end_time: ISO 8601 datetime or null\n"
            "- location_name: venue name\n"
            "- search_term: venue name + city for geocoding\n"
            "- country_code: ISO 2-letter code\n"
            "- category: music / art / sports / tech / food / other\n"
            "- sub_category: specific genre or style\n"
            f"- tags: 2-5 tags from: {', '.join(_GLOBAL_TAGS)}\n\n"
            f"Text:\n{cleaned_text}"
        )

        try:
            response = _client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                extra_body={"thinking": {"type": "disabled"}},
            )
            raw_json: str | None = response.choices[0].message.content
            return cls._parse_deepseek_response(raw_json, source_domain)
        except Exception as exc:
            logger.error("DeepSeek extraction failed: %s", exc)
            return []

    @classmethod
    def _parse_deepseek_response(
        cls,
        raw_json: str | None,
        source_domain: str | None,
    ) -> list[ExtractedEvent]:
        """Parse a JSON string from DeepSeek into ExtractedEvent objects.

        Returns [] on missing content, malformed JSON, or per-item validation errors.
        """
        if not raw_json:
            return []
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.warning("DeepSeek returned malformed JSON: %s", exc)
            return []

        raw_events = data.get("events", [])
        if not isinstance(raw_events, list):
            logger.warning("DeepSeek 'events' field is not a list; returning empty.")
            return []

        events: list[ExtractedEvent] = []
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            try:
                ev = ExtractedEvent.model_validate(item)
                ev.source_provider = source_domain or "unknown"
                ev.ingestion_method = "html_fallback"
                events.append(ev)
            except Exception as exc:
                logger.warning("Skipping malformed event item from DeepSeek: %s", exc)
        return events

    # ------------------------------------------------------------------
    # Instructor path: Gemini and other instructor-compatible providers
    # ------------------------------------------------------------------

    @classmethod
    def _extract_instructor(
        cls,
        cleaned_text: str,
        country_hint: str | None,
        source_domain: str | None,
    ) -> list[ExtractedEvent]:
        """Call the provider via instructor structured-output (Gemini / legacy path)."""
        user_prompt = (
            f"Extract event details from the following text.\n"
            f"Return a JSON list of events. Context country: {country_hint or 'Global'}.\n\n"
            "MANDATORY: Do NOT include 'description' or 'photo_url' in your output.\n\n"
            "Details to provide:\n"
            "- title: The name of the event\n"
            "- location_name: The name of the venue\n"
            "- search_term: descriptive term for geocoding (venue name + city)\n"
            "- city_hint: City/neighborhood\n"
            "- street_address: specific street name and number\n"
            "- sub_category: Identify specific genre/vibe\n"
            f"- tags: Select 2-5 tags from: {', '.join(_GLOBAL_TAGS)}.\n\n"
            f"Text: {cleaned_text}"
        )

        try:
            response = _client.chat.completions.create(
                model=settings.AI_MODEL,
                max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=IterableExtractedEvent,
            )
            events: list[ExtractedEvent] = response.tasks
            for ev in events:
                ev.source_provider = source_domain or "unknown"
                ev.ingestion_method = "html_fallback"
            return events
        except Exception as exc:
            logger.error("AI extraction failed: %s", exc)
            return []
