from typing import Any, ClassVar


class EventClassifier:
    """
    Domain service for classifying events based on title, description, and metadata.
    Follows FOMO classification standards.
    """

    MUSIC_MAP: ClassVar[dict[str, str]] = {
        "techno": "Techno",
        "house": "House",
        "jazz": "Jazz",
        "rock": "Rock",
        "hip hop": "Hip-Hop",
        "rap": "Hip-Hop",
        "classical": "Classical",
        "rebetiko": "Rebetiko",
        "laiko": "Laiko",
        "pop": "Pop",
        "electronic": "Electronic",
        "metal": "Metal",
        "blues": "Blues",
        "punk": "Punk",
        "indie": "Indie",
        "dj set": "Electronic",
        "party": "Electronic",
    }

    MUSIC_KEYWORDS: ClassVar[list[str]] = [
        "concert",
        "συναυλία",
        "μουσική",
        "live",
        "tour",
        "περιοδεία",
        "βραδιά",
        "guest",
        "performance",
    ]

    @classmethod
    def classify(
        cls, title: str, description: str | None, metadata: dict[str, Any]
    ) -> tuple[str, str | None, list[str]]:
        """
        Extracts category, sub-category, and tags from event text and metadata.
        """
        title_lower = title.lower()
        desc_lower = (description or "").lower()
        combined_text = f"{title_lower} {desc_lower}"

        category = "Other"
        sub_category = None
        tags: list[str] = []

        # 1. Type-based initial classification
        item_type_raw = metadata.get("@type", "")
        item_types = (
            item_type_raw if isinstance(item_type_raw, list) else [str(item_type_raw).lower()]
        )
        type_str = " ".join([str(t).lower() for t in item_types])

        if "music" in type_str or "concert" in type_str:
            category = "Music"
        elif "art" in type_str:
            category = "Art"
        elif "theater" in type_str:
            category = "Art"
            sub_category = "Theater"

        # 2. Keyword-based music enrichment
        for kw, val in cls.MUSIC_MAP.items():
            if kw in combined_text:
                category = "Music"
                sub_category = val
                tags.append(val)
                break

        if category == "Other":
            if any(kw in combined_text for kw in cls.MUSIC_KEYWORDS):
                category = "Music"

        # 3. Metadata-based refinement
        organizer = metadata.get("organizer", {})
        organizer_name = ""
        if isinstance(organizer, dict):
            organizer_name = str(organizer.get("name") or "").lower()
        elif isinstance(organizer, str):
            organizer_name = organizer.lower()

        if any(kw in organizer_name for kw in ["festival", "productions", "music"]):
            category = "Music"

        if "festival" in combined_text or "φεστιβάλ" in combined_text:
            if "Festival" not in tags:
                tags.append("Festival")
            category = "Music"

        # 4. Source-based hint
        source_domain = metadata.get("source_domain")
        if source_domain and "/music/" in str(source_domain).lower():
            category = "Music"

        return category, sub_category, list(set(tags))
