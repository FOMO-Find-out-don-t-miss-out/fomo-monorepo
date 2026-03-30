from pathlib import Path
from typing import Any

import yaml


class TaxonomyManager:
    """
    Manages the hierarchical taxonomy for event classification.
    Loads from taxonomy.yaml and provides matching logic.
    """

    def __init__(self, taxonomy_path: Path | str | None = None) -> None:
        if taxonomy_path is None:
            # Default to the one in packages/domain/resources/
            current_file = Path(__file__).resolve()
            taxonomy_path = current_file.parents[1] / "resources" / "taxonomy.yaml"

        with Path(taxonomy_path).open(encoding="utf-8") as f:
            self.data: dict[str, Any] = yaml.safe_load(f)

    def find_match(self, text: str) -> tuple[str, str | None, list[str]]:
        """
        Performs keyword matching across all categories and sub-categories.
        Prioritizes sub-category matches.

        Returns:
            tuple: (category, sub_category, tags)
        """
        text_lower = text.lower()
        matched_category = "Other"
        matched_sub_category = None
        tags: list[str] = []

        categories = self.data.get("categories", {})

        # 1. Try to find a sub-category match first (more specific)
        for cat_name, cat_data in categories.items():
            sub_categories = cat_data.get("sub_categories", {})
            for sub_name, sub_data in sub_categories.items():
                keywords = sub_data.get("keywords", [])
                if any(kw.lower() in text_lower for kw in keywords):
                    return cat_name, sub_name, [sub_name]

        # 2. Try to find a category-level match
        for cat_name, cat_data in categories.items():
            category_keywords = cat_data.get("keywords", [])
            if any(kw.lower() in text_lower for kw in category_keywords):
                matched_category = cat_name
                break

        return matched_category, matched_sub_category, tags
