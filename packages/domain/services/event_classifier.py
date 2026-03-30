from typing import Any, ClassVar

from packages.domain.services.taxonomy_manager import TaxonomyManager


class EventClassifier:
    """
    Domain service for classifying events based on title, description, and metadata.
    Follows FOMO classification standards.
    """

    _taxonomy_manager: ClassVar[TaxonomyManager] = TaxonomyManager()

    @classmethod
    def classify(
        cls, title: str, description: str | None, metadata: dict[str, Any]
    ) -> tuple[str, str | None, list[str]]:
        """
        Extracts category, sub-category, and tags from event text and metadata.
        Uses the TaxonomyManager for keyword-based matching and metadata for refinement.
        """
        title_lower = title.lower()
        desc_lower = (description or "").lower()
        combined_text = f"{title_lower} {desc_lower}"

        # 1. Keyword-based lookup using TaxonomyManager
        category, sub_category, tags = cls._taxonomy_manager.find_match(combined_text)

        # 2. Type-based initial classification (refinement)
        item_type_raw = metadata.get("@type", "")
        item_types = (
            item_type_raw if isinstance(item_type_raw, list) else [str(item_type_raw).lower()]
        )
        type_str = " ".join([str(t).lower() for t in item_types])

        if "music" in type_str or "concert" in type_str:
            category = "Music"
        elif "art" in type_str:
            category = "Arts"
        elif "theater" in type_str:
            category = "Arts"
            sub_category = "Theater"

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
            if category == "Other":
                category = "Music"

        # 4. Source-based hint
        source_domain = metadata.get("source_domain")
        if source_domain and "/music/" in str(source_domain).lower():
            category = "Music"

        return category, sub_category, list(set(tags))
