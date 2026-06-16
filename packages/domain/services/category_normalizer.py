from packages.domain.models.event import EventCategory

# Reserved sentinel used by TrustEngine.is_junk() to flag AI-detected junk
# (ads/promos misdetected as events). Must pass through untouched — it is
# not a real category and must never be coerced to "Other".
_JUNK_SENTINEL = "Junk"

# Source/display labels (lowercased) that map to a canonical EventCategory.
# This is the single place that reconciles inconsistent source-provided or
# AI-extracted category strings (e.g. More.com's "Live Music", a lowercase
# AI completion like "music") with the stable backend taxonomy.
_CATEGORY_ALIASES: dict[str, EventCategory] = {
    "music": EventCategory.Music,
    "live music": EventCategory.Music,
    "concert": EventCategory.Music,
    "concerts": EventCategory.Music,
    "gig": EventCategory.Music,
    "dj set": EventCategory.Music,
    "dj": EventCategory.Music,
    "art": EventCategory.Art,
    "arts": EventCategory.Art,
    "theater": EventCategory.Art,
    "theatre": EventCategory.Art,
    "exhibition": EventCategory.Art,
    "tech": EventCategory.Tech,
    "technology": EventCategory.Tech,
    "food": EventCategory.Food,
    "food & drink": EventCategory.Food,
    "food and drink": EventCategory.Food,
    "nightlife": EventCategory.Nightlife,
    "club": EventCategory.Nightlife,
    "clubbing": EventCategory.Nightlife,
    "sports": EventCategory.Sports,
    "sport": EventCategory.Sports,
    "business": EventCategory.Business,
    "community": EventCategory.Community,
    "other": EventCategory.Other,
}


def normalize_category(raw: str | None) -> str:
    """
    Resolve any source/AI-provided category string to a canonical
    EventCategory value. Falls back to EventCategory.Other when the input
    is missing or unrecognized.
    """
    if not raw:
        return EventCategory.Other.value

    trimmed = raw.strip()
    if not trimmed:
        return EventCategory.Other.value

    if trimmed == _JUNK_SENTINEL:
        return _JUNK_SENTINEL

    try:
        return EventCategory(trimmed).value
    except ValueError:
        pass

    alias = _CATEGORY_ALIASES.get(trimmed.lower())
    if alias is not None:
        return alias.value

    for member in EventCategory:
        if member.value.lower() == trimmed.lower():
            return member.value

    return EventCategory.Other.value
