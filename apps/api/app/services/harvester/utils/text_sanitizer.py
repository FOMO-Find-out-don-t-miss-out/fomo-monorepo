import html
import re


class TextSanitizer:
    """Utility class for cleaning and normalizing scraped text."""

    @staticmethod
    def clean_title(text: str) -> str:
        """
        Cleans an event title by:
        1. Decoding HTML entities.
        2. Removing common site-specific suffixes (e.g., | MORE.COM).
        3. Applying smart capitalization (Title Case).
        4. Normalizing whitespace.
        """
        if not text:
            return ""

        # 1. Decode HTML entities (e.g., &amp; -> &)
        text = html.unescape(text)

        # 2. Remove common site-specific suffixes
        suffixes = [
            r"\s*\|\s*MORE\.COM\s*",
            r"\s*\|\s*VIVA\.GR\s*",
            r"\s*\|\s*TICKETMASTER\s*",
            r"\s*-\s*MORE\.COM\s*",
            r"\s*-\s*VIVA\.GR\s*",
        ]
        for suffix in suffixes:
            text = re.sub(suffix, "", text, flags=re.IGNORECASE)

        # 3. Smart capitalization (Title Case)
        # If the text is all caps, all lowercase, or contains long sequences of caps
        if text.isupper() or text.islower() or re.search(r"[A-Z]{4,}", text):
            text = text.title()

        # 4. Normalize whitespace
        text = TextSanitizer.normalize_whitespace(text)

        return text.strip()

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Removes double spaces, tabs, and trailing newlines.
        """
        if not text:
            return ""

        # Replace tabs and newlines with spaces
        text = re.sub(r"[\t\r\n]+", " ", text)

        # Replace multiple spaces with a single space
        text = re.sub(r"\s{2,}", " ", text)

        return text.strip()
