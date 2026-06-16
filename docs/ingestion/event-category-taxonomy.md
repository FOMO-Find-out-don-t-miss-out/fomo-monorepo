# Event Category Taxonomy (FOMO-166)

## Why this exists

Most events ingested from More.com are concerts. The dashboard's category
filter offered a hand-invented label set (`Live Music`, `Theater`,
`Food & Drink`, ...) that shared no values with what the backend actually
stores, so selecting `Live Music` silently returned zero results. Separately,
the AI/LLM extraction path (DeepSeek) was prompted to return lowercase
category strings (`"music"`), and the cleansing pipeline's "only override
when the value is exactly `Other`" check let that miscased value bypass the
domain classifier — so identical concerts ended up stored as both `Music`
and `music` depending on which extraction path produced them. This document
defines the single canonical taxonomy both paths and the dashboard now use.

## Canonical category values

The canonical, stable category values are the backend's `EventCategory`
enum (`packages/domain/models/event.py`):

```
Music, Art, Tech, Food, Nightlife, Sports, Business, Community, Other
```

These are the values stored in the `category` column on both `PendingEvent`
and `Event`, and the only values the dashboard's category filter and edit
form send to the API. Nothing else should ever be persisted as a category —
display labels and source-specific labels (below) are mapped into one of
these before they reach the database.

`sub_category` remains a free-form string used for finer-grained genre/style
tagging (e.g. `Techno`, `Jazz`, `Theater`) and is not part of the canonical
top-level taxonomy.

## Display labels vs. canonical values

The dashboard shows friendlier labels for some categories (most notably
`Music` → "Live Music", since that's what the vast majority of ingested
events actually are), but **always filters, queries, and edits using the
canonical value**. This mapping lives in `categoryLabel()` /
`EVENT_CATEGORIES` in `apps/harvester-dashboard/lib/utils.ts`. A display
label is never stored as a category — only canonical values are.

| Canonical value | Dashboard display label |
| --- | --- |
| `Music` | Live Music |
| `Art` | Art |
| `Tech` | Tech |
| `Food` | Food & Drink |
| `Nightlife` | Nightlife |
| `Sports` | Sports |
| `Business` | Business |
| `Community` | Community |
| `Other` | Other |

## Source-label mapping rules

Source systems (More.com, AI extraction) often produce text that isn't an
exact canonical value: lowercase strings, synonyms, or alternate spellings
(`Live Music`, `concert`, `dj set`, `arts`, `theatre`, `food and drink`,
`club`, ...). `packages/domain/services/category_normalizer.py` is the single
place that reconciles this: `normalize_category(raw)` does a case-insensitive
exact match against `EventCategory` first, then checks a small alias table,
and falls back to `Other` for anything unrecognized.

`ExtractedEvent.category` (`packages/domain/schemas/extracted_event.py`)
calls `normalize_category()` in its `ensure_category` validator, so **every**
extraction path — JSON-LD, AI/HTML fallback, and the public ingestion API —
normalizes category at the same schema boundary before it ever reaches the
cleansing pipeline or the database. This is what fixed the lowercase
`"music"` bug: it is normalized to `"Music"` immediately on construction,
so `CleansingService.clean_html_fallback()`'s `if event.category == "Other"`
override check now reliably means "no real category was found," instead of
silently keeping a miscased AI value.

One reserved sentinel, `"Junk"`, intentionally bypasses normalization —
`TrustEngine.is_junk()` uses that literal value to flag AI-detected
ads/non-events, and it is not a real category.

## How `Other` should be used

`Other` means "no music/art/tech/etc. signal was found in the title,
description, or metadata" — it is the conservative fallback, not a sign of
broken classification. `EventClassifier.classify()`
(`packages/domain/services/event_classifier.py`) combines:

1. Keyword matching against `packages/domain/resources/taxonomy.yaml`
   (sub-category keywords first, then category-level keywords).
2. Schema.org `@type` refinement (`MusicEvent` → `Music`, `TheaterEvent` →
   `Art` + `Theater` sub-category).
3. Organizer-name and source-domain hints (e.g. a `more.com/music/...` URL).
4. A festival/φεστιβάλ keyword check that nudges an otherwise-`Other` result
   to `Music`, since festivals on More.com are overwhelmingly music events.

It does **not** guess from venue name alone, and it does not bias every
More.com event toward `Music` by default — only events with an actual
music/art/tech/festival signal are reclassified. An event with a bare title
and no recognizable keywords legitimately stays `Other`.

## More.com mapping behavior

`MoreComProvider` (`apps/api/app/services/harvester/providers/more_com.py`)
never assigns category itself — it only fetches event data via three tiers
(CSS-selector registry extraction, Schema.org JSON-LD, raw-text AI
fallback). Category is always resolved downstream:

- JSON-LD events always go through `CleansingService.clean_json_ld()`, which
  unconditionally overwrites category with `EventClassifier.classify()` —
  always canonical.
- AI/raw-text fallback events go through `clean_html_fallback()`, which now
  trusts the AI's (normalized) category unless it resolved to `Other`, in
  which case the domain classifier's result is used instead.

## Known follow-ups

- `taxonomy.yaml` only defines keywords for `Music`, `Art`, and `Tech`.
  `Food`, `Nightlife`, `Sports`, `Business`, and `Community` exist in the
  `EventCategory` enum but currently have no keyword coverage, so events in
  those domains can only be reclassified out of `Other` via the AI
  extraction path, not the JSON-LD keyword path. Extending `taxonomy.yaml`
  for those categories is a separate, deliberate product/taxonomy decision
  (not done here, to avoid inventing over-specific categories speculatively).
- Richer event-format subcategories (e.g. `live_music` / `concert` / `dj_set`
  as distinct from music genre subcategories like `Techno`/`Jazz`) are a
  possible future enhancement; the current `sub_category` field already
  supports this without a schema change if/when product wants it.
- Historical events already stored with `category="Other"` are **not**
  bulk-backfilled by this change. Run
  `uv run python tooling/report_other_category_events.py` for a read-only
  dry-run report of events where the current classifier would now suggest a
  non-`Other` category — review it manually before deciding whether/how to
  apply any fixes.
