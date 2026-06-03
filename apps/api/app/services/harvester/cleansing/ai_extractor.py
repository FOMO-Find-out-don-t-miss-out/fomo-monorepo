import logging
import re
from typing import Any

import instructor
from app.core.config import settings
from bs4 import BeautifulSoup

from packages.domain.schemas.extracted_event import ExtractedEvent, IterableExtractedEvent

logger = logging.getLogger(__name__)

# _client holds the active instructor-wrapped API client, or None when disabled.
# The FOMO-131 test guard (conftest.py) replaces this with a sentinel that raises
# RuntimeError on any call, preventing accidental paid API hits during tests.
_client: Any = None


def _init_client() -> Any:  # noqa: ANN401
    """Return an instructor-patched client based on current settings, or None."""
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

            raw = OpenAI(
                api_key=api_key,
                base_url=settings.AI_BASE_URL,
                timeout=float(settings.AI_REQUEST_TIMEOUT_SECONDS),
            )
            logger.info("DeepSeek AI client initialized (model=%s).", settings.AI_MODEL)
            return instructor.from_openai(raw)
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

_SYSTEM_PROMPT = (
    "You are a professional event data extractor.\n"
    "Return ONLY valid JSON. No explanations.\n\n"
    "Extraction Rules:\n"
    "1. Extract ONLY: Title, Start Time, End Time, and Venue details.\n"
    "2. DO NOT extract descriptions or image URLs under any circumstances.\n"
    "3. Strict Classification Hierarchy: Venue blindness, "
    "forbid 'Other' if musical keywords are present."
)


class AiExtractor:
    """Extracts structured event data from unstructured HTML using the configured LLM."""

    @staticmethod
    def _strip_html_noise(html_text: str) -> str:
        """Strips scripts, styles, nav/footer/header, and collapses whitespace."""
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
        """Strip noise from HTML and call the configured LLM to extract event data."""
        if not _client:
            logger.debug("AI client not configured. Skipping extraction.")
            return []

        cleaned_text = cls._strip_html_noise(html_text)
        if len(cleaned_text) < 50:
            return []

        # Cost control: cap input to configured limit before sending to the model.
        if len(cleaned_text) > settings.AI_MAX_INPUT_CHARS:
            logger.debug(
                "AI input truncated %d → %d chars.",
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

            events = response.tasks
            for ev in events:
                ev.source_provider = source_domain or "unknown"
                ev.ingestion_method = "html_fallback"
            return events
        except Exception as exc:
            logger.error("AI extraction failed: %s", exc)
            return []
