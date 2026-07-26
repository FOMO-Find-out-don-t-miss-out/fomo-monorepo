# FOMO Mobile — Explore UI

> **Canonical design reference for the Explore screen and its components.**
> Approved and committed UI architecture. Physical Android validation required
> for any future changes.

---

## 1. Purpose and status

**Status:** Production — committed and physically validated on Android.

**Scope:** The Explore tab (`apps/mobile/app/(tabs)/search.tsx`) and its
dedicated components. This document records the final approved implementation
and the binding product decisions made during FOMO-172 Phase 6.

---

## 2. Discover versus Explore responsibilities

| | Discover | Explore |
|---|---|---|
| **Role** | Map-first serendipitous browsing | Intentional multi-entity search |
| **Primary surface** | Map (`FomoMap`) + carousel | Search input + result list |
| **Input** | None required (location is ambient) | Query text, filters, entity scope |
| **Reached via** | Tab 1 (Home) | Tab 2 (Explore) — bottom navigation |
| **Owns** | Map, pins, nearby carousel, calendar view, local category chips | Search input, entity tabs, filters, result list, EventDetails |
| **Does not own** | Text search, multi-entity results, backend search | Map, serendipitous discovery, calendar view |

**Binding rule:** Discover has no search/Explore launcher. Explore is reached
from the bottom-navigation Explore tab. Discover remains map-first; Explore
remains the intentional search destination.

---

## 3. Final Discover header

**Commit:** `268960b` — FOMO-172: simplify Discover map header

The Discover header is a single compact row containing only local controls:

```
┌──────────────────────────────────────────────────┐
│ FOMO                        [Filter] [Cal] [Bell]│
└──────────────────────────────────────────────────┘
```

- **FOMO logo:** 15px ExtraBold, `Colors.brandPrimary`, neon purple glow.
  Sits directly on the map — no container, no divider, no button.
- **Filter button:** 40×40 `surfaceGlass`/`borderGlass`. Opens Discover's
  local category filter panel. Active-category badge.
- **Calendar/Map toggle:** 40×40. Purple-dim when calendar is active.
- **Bell:** 40×40. Purple dot indicator.

No `TextInput`, no placeholder text, no launcher. Discover's `SearchBar`
(`apps/mobile/components/fomo/search-bar.tsx`) owns this header and the
local category-filter panel.

---

## 4. Final Explore shell

**Commit:** `be36ce6` — FOMO-172: refine Explore search shell

The Explore screen uses a **fixed shell above FlatList** architecture.
The shell never scrolls away. No `ListHeaderComponent`. No nested
`ScrollView` wrapping `FlatList`.

### Vertical hierarchy

```
1. Explore title            ← 20px ExtraBold, insets.top + 16
2. Search input + filter    ← 44px input + 44×44 filter button
3. Entity scope tabs        ← text-first underline tabs, 44px touch
4. Active-filter chips      ← horizontal scroller + "Clear all"
5. "EVENTS" section heading ← 11px Bold uppercase (when results present)
6. FlatList / state content ← virtualized, paginated
7. EventDetails overlay     ← existing shared component
```

### Spacing contract

| Boundary | Spacing |
|----------|---------|
| Safe area top → title | `insets.top + Spacing.base` (16px) |
| Title → search row | `Spacing.md` (12px) |
| Search row → entity tabs | `Spacing.lg` (20px) |
| Entity tabs → filter chips | `Spacing.sm` (8px) |
| Filter chips → section heading | `Spacing.sm` (8px) |
| Section heading → first result | `Spacing.sm` (8px) |

### Horizontal alignment grid

All shell elements share `paddingHorizontal: Spacing.base` (16px):
title, search row, entity tabs, filter chips, section heading, state area.

### Search + filter row

```
[ ExploreSearchInput, flex: 1, minWidth: 0 ] [ filter button, 44×44 fixed ]
```

- Input wrapper: `flex: 1`, `minWidth: 0` — prevents filter button overflow
- Filter button: fixed 44×44, `flexShrink: 0`, `SlidersHorizontal` icon
- Filter badge: 0–3 active groups, 16px purple circle, absolute top-right
- `gap: Spacing.sm` (8px) between input and filter button

The filter button is a separate control, not inside the input. It must never
render outside the viewport at 360px.

---

## 5. Entity scopes and honest counts

Five local scopes implemented as text-first underline tabs inside a
horizontal `ScrollView`:

| Scope | Count | Backend |
|-------|-------|---------|
| **All** | Same honest count as Events | N/A (grouped view) |
| **Events** | `N` when `hasMore=false`, `N+` when `hasMore=true` | Real API |
| **Organizers** | `0` | No endpoint — future |
| **People** | `0` | No endpoint — future |
| **Places** | `0` | No endpoint — future |

### Tab specification

- **Label:** 14px Medium, `textMuted` → `textPrimary` + `SemiBold` when active
- **Count:** 9px, inline beside label with 6px gap, `textMuted` → `brandPrimary` when active
- **Indicator:** 2px purple bar, absolute bottom, spans tab horizontal padding
- **Touch:** `minHeight: 44`, `paddingVertical: 12`, `paddingHorizontal: 12`
- **Divider:** `hairlineWidth` bottom border on tabs container
- **Overflow:** Horizontal scroll with auto-scroll-to-selected
- **Accessibility:** `role="tab"`, `accessibilityState={{ selected }}`

### Scope behavior

Switching entity scope does not alter: query text, active filters,
loaded Events results, inherited Near me state, or pagination state.
Events search continues regardless of selected scope.

Future scopes render confident product-facing zero-states:

- **Organizers:** "No organizers found" / "Organizer discovery is being prepared."
- **People:** "No people found" / "People discovery will appear here."
- **Places:** "No places found" / "Place search is being connected."

No network requests to nonexistent endpoints. No mock data. No fake counts.

---

## 6. Search and filter control hierarchy

### ExploreSearchInput

**File:** `apps/mobile/components/fomo/explore-search-input.tsx`

A screen-embedded editable search field. Deliberately not the Discover
`SearchBar`: no floating layout, no BlurView, no filter/calendar/bell
controls.

| Property | Value |
|----------|-------|
| Height | 44px |
| Border radius | `Radii.lg` (14) |
| Border width | 1px (constant — focus changes color, not width) |
| Resting border | `Colors.borderGlass` |
| Focused border | `Colors.borderFocus` |
| Background | `Colors.surfaceGlass` |
| Leading icon | `Search` 18px, `Colors.textSecondary` |
| Input font | 15px, `Colors.textPrimary` |
| Placeholder | "Search events by name, venue, or organizer" |
| Placeholder color | `Colors.textMuted` |
| Clear button | `X` 16px, 40×40 touch via `hitSlop: 8` |
| Android | `textAlignVertical: 'center'`, `padding: 0`, `margin: 0` |

### Filter button

44×44 square, `surfaceGlass`/`borderGlass` resting, `borderFocus`/`purpleDim`
pressed. `SlidersHorizontal` 20px icon. Purple badge (0–3 groups). Groups:
categories, date, Near me — radius does not count separately.

### ExploreFilterModal

**File:** `apps/mobile/components/fomo/explore-filter-modal.tsx`

85% tall bottom sheet with sticky footer. Preserves all filter semantics
(draft state, double-Apply guard, Near me blocking, location snapshot). Drag
handle, per-category chip colors with Check icons on selection, distinct
Near me location card, conditionally visible distance controls.

#### Action footer

The footer is outside the `ScrollView` — always reachable. A hairline
separator sits above it.

```
┌────────────────────────────────────────────┐
│ ────────────────────────────────────────   │ ← separator
│ [ Reset filters ]    [  Show events  ]     │ ← action row
└────────────────────────────────────────────┘
```

| Property | Reset filters | Show events |
|----------|--------------|-------------|
| **Component** | `TouchableOpacity`, static `style` | `TouchableOpacity` > `LinearGradient`, static `style` |
| **Width** | 116px (`flexShrink: 0`) | `flex: 1`, `minWidth: 0`, `marginLeft: 12` |
| **Height** | 48px | 48px |
| **Border radius** | `Radii.md` (12px) | `Radii.md` (12px) |
| **Surface** | `Colors.surfaceGlass` + 1px `Colors.borderGlass` | `Gradients.primaryCta` (`#BC13FE` → `#9333EA`) |
| **Label** | 13px SemiBold, `textSecondary`, centered | 14px Bold, `textPrimary`, centered |
| **Press** | Native `activeOpacity={0.7}` | Native `activeOpacity={0.78}` |
| **Disabled** | N/A (always enabled) | `opacity: 0.45` when `nearMeBlocked` |
| **Layout shift** | None | None — same 48px height and `flex: 1` width when disabled |

#### Action semantics

- **Reset filters:** Modifies local draft state only. Does not close the
  modal, does not fire a search, does not commit changes. User must press
  "Show events" to commit the reset.
- **Show events:** Commits the current draft. Guarded against rapid
  double-submit. Disabled when Near me is selected but location is
  unavailable — same dimensions, no layout shift.

#### Footer geometry rules

- Both controls share identical 48px visual height and identical vertical
  alignment.
- At 360px: Reset = 116px, gap = 12px, Show events = 328 − 116 − 12 = 200px.
- Footer `paddingHorizontal: 16`, `paddingTop: 12`,
  `paddingBottom: max(insets.bottom, 16)`.
- No `FomoButton` is used in this footer. Local `TouchableOpacity` +
  `LinearGradient` controls are intentional because the generic
  `FomoButton` cannot reliably produce the required 48px fixed geometry on
  the target Android device. This is a component-specific decision — it
  does not prohibit `FomoButton` for ordinary standalone CTA usage
  elsewhere.

#### Why local controls

The generic `FomoButton` composition uses a `Pressable` with a functional
style callback inside a `LinearGradient`. On the target Android device,
functional style callbacks do not reliably apply base styles to the native
root. The inner `Pressable` also carries its own `paddingVertical` which
can cause height expansion beyond an externally specified `height`. For
this specific fixed-geometry footer, local `TouchableOpacity` controls
with static `style` props and no internal `Pressable` nesting produce the
exact dimensions verified on physical Android.

This is documented as an implementation decision, not a platform bug or
a `FomoButton` defect.

---

## 7. Active-filter summary

Rendered only when filters are active. One stable horizontal row:

```
[ horizontally scrollable chips, flex: 1 ] [ Clear all, fixed ]
```

- **Row height:** 40px
- **Chips:** `purpleDim` background, `borderFocus` border, 999px radius, removable via `X` icon
- **Clear all:** Fixed trailing `Pressable`, always reachable, underlined semiBold text

Individual category chips, date chip, and Near me/radius chip are each
independently removable. Chips do not wrap into multiple lines.

---

## 8. Explore event-result presentation

**File:** `apps/mobile/components/fomo/explore-event-list-item.tsx`
**Commit:** `2aa29de` — FOMO-172: add branded Explore event result cells

### Architecture

```
TouchableOpacity (static style, activeOpacity 0.65, accessibilityRole="button")
├── Thumbnail (56×56, always present, flexShrink: 0)
│   ├── FOMO fallback (always underneath — category bg + "FOMO" text)
│   └── Image (absoluteFill) — only when imageUri exists and hasn't failed
├── Gap: 10px (marginLeft on content column)
└── Content column (flex: 1, minWidth: 0, flexShrink: 1)
    ├── Title: 14px SemiBold, 2 lines, textPrimary
    ├── Date/time: 11px, textMuted, "{date} · {time}" — omitted when date is "TBA"
    └── Venue + category footer row
        ├── Venue: flex: 1, 12px, textSecondary — omitted when "TBA"
        └── Category: flexShrink: 0, 10px Medium, exploreCategory color
```

### Cell surface

| Property | Value |
|----------|-------|
| Background | `Colors.surfaceCard` |
| Border | `StyleSheet.hairlineWidth`, `Colors.borderSubtle` |
| Border radius | 12px |
| Horizontal margin | 16px |
| Vertical margin | 8px bottom |
| Internal padding | 10px horizontal + vertical |
| Layout | `flexDirection: 'row'`, `alignItems: 'center'` |

The cell is a complete horizontal composition. Every cell has the same
structure regardless of image availability. The entire cell opens
EventDetails — no "View Details" button, no child actions.

### Content hierarchy

1. **Title** — 14px SemiBold, `Colors.textPrimary`, `lineHeight: 18`, 2 lines max, `numberOfLines: 2`
2. **Date/time** — 11px Regular, `Colors.textMuted`, `"{date} · {time}"`, omitted when date is `"TBA"`
3. **Venue** — 12px Regular, `Colors.textSecondary`, 1 line, omitted when `"TBA"`
4. **Category** — 10px Medium, per-category `exploreCategory` color, `flexShrink: 0`

At 360px, the content column receives approximately 242px:
`360 − 32 (margins) − 20 (cell padding) − 56 (thumbnail) − 10 (gap) = 242px`.

### Width budget (360px)

| Layer | Consumed | Remaining |
|-------|----------|-----------|
| Screen | — | 360px |
| Cell margin (2×16) | 32px | 328px |
| Cell padding (2×10) | 20px | 308px |
| Thumbnail | 56px | 252px |
| Content marginLeft | 10px | **242px** |

---

## 9. FOMO fallback-thumbnail system

Every result has a fixed 56×56 thumbnail slot. When a real image exists it
overlays the fallback via `StyleSheet.absoluteFillObject`. When no image
exists or an image fails to load, the branded FOMO fallback is visible.

### Fallback specification

| Property | Value |
|----------|-------|
| Size | 56×56 (identical to real image) |
| Border radius | 10px |
| Background | `Colors.exploreCategory[cat].bg` (15% category color on dark) |
| Border | `StyleSheet.hairlineWidth`, `Colors.exploreCategory[cat].border` (40% category color) |
| Content | `"FOMO"` text, centered |
| Font | `Inter_700Bold`, 10px, `letterSpacing: 0.5` |
| Text color | `Colors.exploreCategory[cat].text` |

### Category examples

| Backend key | Display label | Thumbnail color |
|-------------|--------------|-----------------|
| Music | Music | Purple (`#C084FC`) |
| Art | Arts | Pink (`#F472B6`) |
| Tech | Tech | Cyan (`#22D3EE`) |
| Food | Food | Amber (`#FBBF24`) |
| Nightlife | Nightlife | Pink (`#F472B6`) |
| Sports | Sports | Green (`#39FF88`) |
| Business | Business | Orange (`#FB923C`) |
| Community | Community | Violet (`#C084FC`) |
| Other | Other | Grey (`#9CA3AF`) |

### Design rationale

The fallback is intentional branded artwork, not an error state. It provides:

- Consistent layout rhythm — every cell has identical geometry
- Category color communication through the largest visual element
- Subliminal FOMO brand reinforcement at every scroll position
- No `ImageOff`, broken-image icon, or empty rectangle — the tile reads as
  deliberate design, not a missing asset

---

## 10. Real-image loading and failure behavior

| State | What renders |
|-------|-------------|
| `imageUri` exists, loading | `Image` with `absoluteFillObject` over the fallback. Fallback visible during load (no white flash). |
| `imageUri` exists, loads | Real image visible over the fallback. `perfLog('image', ...)` emitted for capped samples. |
| `imageUri` exists, `onError` | `imageFailed` state set to `true`. Image removed. Fallback remains visible. No `perfLog` emitted. |
| `imageUri` is null | Fallback visible from first render. No image component mounted. No instrumentation. |
| `imageUri` changes (FlatList recycling) | `imageFailed` reset to `false` via `useEffect`. Fresh image attempt. |

No layout shift at any transition. Real and fallback cells have identical
width, height, and content alignment.

---

## 11. Category visual mapping

Two independent category systems coexist:

### Discover (6 buckets)

In `Colors.category`, keyed by `UiEventCategory`. Used by `EventCard`
and Discover's local filter chips. Untouched by FOMO-172.

### Explore (9 backend categories)

In `Colors.exploreCategory`, keyed by backend `EventCategory` string.
Used by `ExploreEventListItem` for thumbnail fallback colors and category
text. Each entry has `text`, `bg`, and `border` tokens.

```typescript
// apps/mobile/theme/index.ts — Colors.exploreCategory
exploreCategory: {
  Music:      { border: 'rgba(168, 85,  247, 0.40)', text: '#C084FC', bg: 'rgba(168, 85,  247, 0.15)' },
  Art:        { border: 'rgba(236, 72,  153, 0.40)', text: '#F472B6', bg: 'rgba(236, 72,  153, 0.15)' },
  Tech:       { border: 'rgba(34,  211, 238, 0.40)', text: '#22D3EE', bg: 'rgba(34,  211, 238, 0.15)' },
  Food:       { border: 'rgba(251, 191, 36,  0.40)', text: '#FBBF24', bg: 'rgba(251, 191, 36,  0.15)' },
  Nightlife:  { border: 'rgba(236, 72,  153, 0.40)', text: '#F472B6', bg: 'rgba(236, 72,  153, 0.15)' },
  Sports:     { border: 'rgba(57,  255, 136, 0.40)', text: '#39FF88', bg: 'rgba(57,  255, 136, 0.15)' },
  Business:   { border: 'rgba(249, 115, 22,  0.40)', text: '#FB923C', bg: 'rgba(249, 115, 22,  0.15)' },
  Community:  { border: 'rgba(168, 85,  247, 0.40)', text: '#C084FC', bg: 'rgba(168, 85,  247, 0.15)' },
  Other:      { border: 'rgba(156, 163, 175, 0.40)', text: '#9CA3AF', bg: 'rgba(156, 163, 175, 0.12)' },
},
```

`backendCategoryLabel()` (`apps/mobile/utils/explore-filters.ts`) converts
the backend key `"Art"` to the display label `"Arts"`. All other labels pass
through unchanged.

---

## 12. Floating-navigation clearance

The floating tab bar overlays the bottom of every tab screen. Its total
height from the screen bottom edge is:

```
navWrapper.paddingTop (8)
+ pill (borderWidth×2 + row paddingVertical×2 + tab content ≈ 74)
+ navWrapper.paddingBottom (max(insets.bottom, 16) + 8)
= 90 + Math.max(insets.bottom, 16)
```

The Explore result list adds 16px breathing room:

```typescript
function listBottomPadding(insetsBottom: number): number {
  return TAB_BAR_BASE_HEIGHT + Math.max(insetsBottom, 16) + Spacing.base;
}
// ≈ 122px on Android without bottom inset
// ≈ 140px on devices with insets.bottom = 34
```

Applied to `FlatList.contentContainerStyle.paddingBottom`, state area
`paddingBottom`, and loading-more footer. The final result card and
loading-more spinner must be fully visible above the floating navigation.

`apps/mobile/app/(tabs)/_layout.tsx` is not modified by Explore.

---

## 13. Accessibility requirements

| Element | Role/Label |
|---------|-----------|
| Screen title | `accessibilityRole="header"` via semantic `Text` |
| Search input | Native `TextInput` — platform handles label |
| Clear button | `accessibilityRole="button"`, `accessibilityLabel="Clear search"` |
| Filter button | `accessibilityLabel="Filters, N active"` when count > 0 |
| Entity tab | `accessibilityRole="tab"`, `accessibilityState={{ selected }}` |
| Filter chip remove | `accessibilityLabel="Remove {label}"` |
| Clear all | Tappable underlined `Pressable` |
| Result cell | `accessibilityRole="button"`, `accessibilityHint="Opens event details"`, combined label: `"title, category, date, at time, venue"` |

The category badge and thumbnail fallback are decorative (not separately
accessible). Nested `<Text>` spans within the cell are not separate
accessibility nodes. The combined accessibility label lives on the root
`TouchableOpacity`.

---

## 14. Performance invariants

| Invariant | Mechanism |
|-----------|-----------|
| FlatList virtualization | `FlatList` with stable `keyExtractor` (`event.id`) |
| Memoized result rows | `React.memo(ExploreEventListItemBase)` |
| Stable callbacks | `useCallback` for `renderItem`, `handleEventSelect`, `keyExtractor` |
| No per-row API requests | `useEventRelationships` only for `selectedEventIds` (single event) |
| Pagination | `onEndReached` → `loadMore`, `hasMore` gating |
| Stale-response protection | `generationRef` in `useExploreSearch` |
| Image instrumentation | Capped sample via `perfClaimImageSample()` (same pool as EventCard) |
| No nested ScrollView | Fixed shell above FlatList — single virtualized scroll surface |
| No BlurView on list | Cells use translucent `surfaceCard`, no per-row blur |

---

## 15. Physical Android validation workflow

Visual UI changes require physical Android validation. No other validation
is sufficient.

### Mandatory gates per visual region

| Region | Check |
|--------|-------|
| **Discover header** | Logo, filter/calendar/bell buttons, spacing, map overlay |
| **Explore shell** | Title, search row, entity tabs, chips, section heading, bottom clearance |
| **Event result cell** | Cell surface, thumbnail, title, metadata, category, separator, press |
| **Filter modal** | Sections, controls, footer, safe area |
| **Future entity states** | Organizers, People, Places zero-states |

### Per-gate workflow

1. Static code inspection (JSX structure, StyleSheet completeness)
2. `pnpm --filter @fomo/mobile lint` — must pass
3. `pnpm --filter @fomo/mobile exec tsc --noEmit` — must pass
4. Physical Android screenshot at 360px, 390px, and 412px
5. Physical interaction check (press, scroll, keyboard, EventDetails open/close)
6. Approval or rejection based on physical evidence
7. Commit only after approval

**Lint is not design validation. TypeScript is not layout validation.**
JSX structure is not rendered proof. Implementation reports are not
sufficient without physical evidence.

### Responsive verification widths

Verify at: 360px, 390px, 412px. Every control must remain fully visible
and tappable at every width. Content must not overflow the viewport.

---

## 16. Diagnostic layout workflow

When the rendered layout contradicts the JSX and StyleSheet source:

1. **Do not** make repeated speculative style changes.
2. Add temporary high-contrast diagnostic colors:
   - Root container: solid red (`#FF0000`)
   - Fixed child (thumbnail): solid blue (`#0000FF`)
   - Flexible child (content): solid green (`#00FF00`)
3. Capture a physical Android screenshot.
4. Interpret the diagnostic colors:
   - **Missing root color** → root style is not reaching the rendered native element — inspect the interactive component (e.g., `Pressable` vs `TouchableOpacity` style callback behavior)
   - **Root visible but children stacked vertically** → `flexDirection: 'row'` is not taking effect — inspect parent width, `alignSelf`, or intermediate wrappers
   - **Root and children inline horizontally** → structure is correct; restore production tokens
5. Apply the smallest proven correction.
6. Remove **every** diagnostic color and log.
7. Retest with production semantic tokens.

**Never leave diagnostic styling in committed code.**

---

## 17. Rejected patterns

These patterns were tested and explicitly rejected during FOMO-172 Phase 6
design and implementation. Do not reintroduce them.

| Pattern | Why rejected |
|---------|-------------|
| Discover fake/disabled search field | Visual vocabulary contradiction — looks like an input, behaves like a button |
| Duplicate Explore launcher in Discover | Explore is reached from the bottom tab; a second entry point adds confusion |
| Discover `EventCard` reused vertically in Explore | 260×180px carousel card with "View Details" CTA — wrong density and interaction model for search results |
| Mandatory broken-image icon (`ImageOff`) | Communicates "this product is broken" for events without images (normal in harvested data) |
| Empty media rectangle placeholder | Same visual weight as a real image but communicates nothing |
| Adaptive removal of the thumbnail slot | Creates inconsistent text leading edge — scanning rhythm breaks |
| Optional media that changes text column width | Eye jumps left/right as it scans — poor search ergonomics |
| Event metadata compressed into one eyebrow line (`category · date · time`) | Three distinct pieces of information crammed into one dense line — hard to parse |
| Full-width data-table separators | Spreadsheet aesthetic — wrong emotional register for an events product |
| "View Details" button on every Explore result | Search results should open on row tap; repeated CTA is noise |
| Broad multi-screen redesign in one phase | Too many variables — impossible to isolate visual defects |
| Trusting static reports over physical rendering | Code structure ≠ rendered output — physical screenshots are the only proof |
| Claiming unproven platform bugs | Style callback issues are implementation decisions, not React Native defects |
| Loose Reset text beside a primary CTA | All footer actions must have visible structure — a bare `Pressable` with no surface/border reads as unfinished |
| Primary CTA occupying excessive footer height | Fixed-height actions (48px) — vertical flex, `paddingVertical`, and internal `Pressable` nesting can expand a button beyond its specified `height` on Android |
| Top-left-aligned button text | All action labels must be centered — `alignItems: 'center'`, `justifyContent: 'center'`, `textAlign: 'center'` on the gradient/surface owner |
| Equal-width actions without hierarchy | Primary must dominate — secondary gets a fixed constrained width; primary fills remaining space |
| Using a reusable component only for consistency when it cannot satisfy required geometry | Prefer a local `TouchableOpacity` with static `style` over forcing an incompatible generic button through external height overrides |
| `Pressable` functional style callbacks for fixed-geometry action controls | Use `TouchableOpacity` with static `style` and `activeOpacity` — proven reliable on the target Android device |
| Implementation reports claiming dimensions that are not physically present | Screenshots are the only proof — never assert `116×48` or `flex×48` without a physical measurement |

---

## 18. Future UI-change checklist

Before modifying any Explore UI:

1. [ ] Read this document (`docs/design/mobile-explore-ui.md`).
2. [ ] Read `apps/mobile/DESIGN.md`.
3. [ ] Confirm the change does not affect Discover or EventCard.
4. [ ] Identify which visual region(s) change — one region per phase.
5. [ ] Verify the change at 360px, 390px, and 412px on a physical Android device.
6. [ ] Verify `tsc --noEmit` and `lint` pass.
7. [ ] Verify no functional hook, API contract, or navigation behavior changed.
8. [ ] Verify fallback and real-image cells remain structurally identical.
9. [ ] Verify no diagnostic colors remain in the diff.
10. [ ] Commit only after physical screenshot approval.
