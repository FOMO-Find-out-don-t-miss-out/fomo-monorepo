# FOMO Mobile — Component Inventory

> **Complete inventory of every reusable component in `apps/mobile/components/`.**
> Source of truth for component boundaries, props, memoization, and styling patterns.

---

## Shared UI primitives (`components/ui/`)

### FomoScreen

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoScreen.tsx` |
| **Export** | `FomoScreen` (named) |
| **Props** | `children`, `style?: ViewStyle` |
| **Purpose** | Root dark container for every tab/screen |
| **Style** | `flex: 1, backgroundColor: Colors.background (#0B0B0F)` |
| **Padding** | None — screens manage their own via `useSafeAreaInsets` |

---

### FomoButton

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoButton.tsx` |
| **Export** | `FomoButton` (named) |
| **Props** | `label`, `onPress?`, `variant? ('primary'\|'ghost'\|'danger')`, `icon?`, `disabled?`, `loading?`, `style?` |
| **Purpose** | Single primary action button |
| **Primary** | `LinearGradient` with `Gradients.primaryCta` (`#BC13FE` → `#9333EA`) |
| **Primary loading** | Spinner uses `Colors.textPrimary` (`#FFFFFF`) |
| **Ghost** | 1px border, transparent bg, white secondary text |
| **Danger** | Ghost variant with `Colors.feedbackError` border/text |
| **Memoized** | No (low render frequency per screen) |
| **Dependencies** | `Colors`, `Gradients`, `Radii`, `Spacing`, `Typography` |

---

### FomoIconButton

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoIconButton.tsx` |
| **Export** | `FomoIconButton` (named) |
| **Props** | `icon`, `onPress?`, `active?`, `activeColor? (default Colors.brandPrimary)`, `disabled?`, `size? ('sm'\|'md')`, `style?`, `accessibilityLabel?` |
| **Purpose** | Glass-style icon button for action rows, toggle states |
| **Style** | `borderColor: activeColor@40%` when active, `Colors.borderGlass` otherwise; `surfaceGlass` bg when active |
| **Memoized** | No |

---

### FomoLoadingState

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoLoadingState.tsx` |
| **Export** | `FomoLoadingState` (named) |
| **Props** | `color? (default Colors.brandPrimary)`, `style?` |
| **Purpose** | Centered full-screen `ActivityIndicator` |
| **Style** | `flex: 1, center aligned` |

---

### FomoErrorState

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoErrorState.tsx` |
| **Export** | `FomoErrorState` (named) |
| **Props** | `message? (default "Something went wrong")`, `onRetry?`, `style?` |
| **Purpose** | Centered error with red icon + optional retry button |
| **Retry style** | `Colors.borderFocus` border pill, `Colors.purpleDim` background on press |
| **Dependencies** | `Colors.feedbackError`, `Colors.borderFocus`, `Colors.brandPrimary`, `Colors.purpleDim` |

---

### FomoEmptyState

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoEmptyState.tsx` |
| **Export** | `FomoEmptyState` (named) |
| **Props** | `icon`, `message`, `sub?`, `action? ({label, onPress})`, `style?` |
| **Purpose** | Centered empty state with icon, heading, optional sub + action |
| **Action style** | `Colors.borderFocus` border pill, `Colors.brandPrimary` label, `Colors.purpleDim` on press |
| **Dependencies** | `Colors.borderFocus`, `Colors.brandPrimary`, `Colors.purpleDim` |

---

## Feature components (`components/fomo/`)

### EventCard

| Field | Value |
|-------|-------|
| **File** | `components/fomo/event-card.tsx` |
| **Export** | `EventCard` (memoized) |
| **Props** | `event: Event`, `isActive?`, `onPress?: (id: string) => void`, `categoryLabel?` |
| **Purpose** | **Discover-only** carousel card: image, category badge, title, venue, date/time, CTA |
| **Boundary** | Must not be reused for Explore search results. Explore uses `ExploreEventListItem`. |
| **Architecture** | `Animated.View` (shadow/scale/transform) → `Pressable` (bg/clip/padding) → content |
| **Memoized** | `React.memo` — FOMO-175: stable `onPress` + stable event identity |
| **Press animation** | Spring scale 1→0.97 on press-in, 0.97→1 on press-out |
| **Image loading** | Sampled timing via `perfClaimImageSample` (capped at 6 per session) |
| **Dimensions** | 260×180px, border-radius 16px |
| **Cover image** | `ImageBackground` with `StyleSheet.absoluteFill` |
| **CTA** | `LinearGradient` (`#BC13FE`→`#9333EA`), "View Details" |
| **Styling pattern** | Theme tokens and hardcoded values mixed — **see concerns below** |
| **Dependencies** | `Colors`, `Gradients`, `Shadows`, `LinearGradient`, `ImageBackground` |

**Hardcoded colour concerns (Phase 3D — resolved):**
- ~~Date row: `#22D3EE` (cyan) for date/time text — use `Colors.textSecondary`~~ ✅ Phase 2
- ~~Price: `#22D3EE` (cyan) for price — use `Colors.textPrimary`~~ ✅ Phase 2
- ~~Venue: `rgba(255,255,255,0.5)` — should use `Colors.textSecondary`~~ ✅ Phase 3D
- ~~Distance: `rgba(255,255,255,0.35)` — should use `Colors.textMuted`~~ ✅ Phase 3D
- ~~CTA border: `rgba(188, 19, 254, 0.3)` — should reference theme border token~~ ✅ Phase 3D
- All remaining values use semantic tokens (`Colors.surfaceCard`, `Colors.textPrimary`, `Colors.eventSelected`, `Colors.borderFocus`)

---

### MyEventListItem

| Field | Value |
|-------|-------|
| **File** | `components/fomo/my-events/MyEventListItem.tsx` |
| **Export** | `MyEventListItem` (memoized) |
| **Props** | `event: UiEvent`, `intent: EventIntent`, `isPending?`, `onPress: (id: string) => void` |
| **Purpose** | My Events list row: accent bar, title, category chip, time, venue, intent dot |
| **Memoized** | `React.memo` — FOMO-178: stable `onPress` + stable event identity |
| **Left accent** | 3px bar, category colour |
| **Intent dot** | 7px circle, coloured by intent |
| **Dimensions** | `minHeight: 60` |
| **Styling** | `Colors.surfaceCard` bg, `Colors.borderSubtle` border, `Radii.md` rounded |
| **Dependencies** | `Colors`, `Radii`, `Spacing`, `Typography` |

**Colour concerns (Phase 1 ✅, Phase 3D ✅ — all resolved):**
- ~~Interested dot: `Colors.magenta` → `Colors.purple`~~ ✅ Phase 1
- ~~Going dot: `Colors.success` → `Colors.neonGreen`~~ ✅ Phase 1
- ~~Time: `#22D3EE` → `Colors.textSecondary`~~ ✅ Phase 3D

---

### IntentSelector

| Field | Value |
|-------|-------|
| **File** | `components/fomo/IntentSelector.tsx` |
| **Export** | `IntentSelector` (named) |
| **Props** | `intent: EventIntent`, `pending?: boolean`, `onSelect: (intent) => void` |
| **Purpose** | Two-button row: "Interested" and "Going" — used in EventDetails (shared by Discover and My Events) |
| **Layout** | Row, equal-width buttons, `flex: 1` each |
| **Visual** | 1.5px border, 13px vertical padding, `Radii.md` rounded |
| **Active state** | Coloured border + tinted background at 20% |
| **Loading state** | Per-button spinner replaces icon |
| **Dependencies** | `Colors`, `Radii`, `Typography` |

**Colour concerns (P1):**
- "Interested" button: `Colors.magenta` — must be `Colors.purple`
- "Going" button: `Colors.cyan` — must be `Colors.neonGreen`

---

### EventDetails

| Field | Value |
|-------|-------|
| **File** | `components/fomo/event-details.tsx` |
| **Export** | `EventDetails` (named) |
| **Props** | `event: Event | null`, `onClose`, `intent?`, `onToggleIntent?`, `isPendingIntent?` |
| **Purpose** | Bottom sheet modal with full event details: badges, title, venue, date/time, intent selector, actions, ticket CTA |
| **Architecture** | `Modal` (transparent, `animationType="none"`), `Animated.View` sheet with `BlurView`, `ScrollView` content |
| **Animation** | Slide-up 300ms `Easing.out(poly(4))`, fade backdrop 200ms. Exit: 220ms slide-down, 180ms fade |
| **Sheet height** | 42% of screen height |
| **Blur** | `BlurView intensity=20` dark tint on entire sheet (single layer, not nested) |
| **Fallback** | `Colors.surface (rgba(12,12,18,0.95))` — Android-safe, readable when blur unavailable |
| **CTA** | `LinearGradient` (`#BC13FE`→`#9333EA`), `Shadows.ctaGlow` applied |
| **Actions** | Directions (Google Maps deep link), Share |
| **Dependencies** | `BlurView`, `LinearGradient`, `Modal`, `Linking`, `Share` |

**Phase 4 ✅ — Blur architecture confirmed correct:**
- Single BlurView(intensity=20) layer — no nested blur
- Fallback uses Colors.surface — readable on Android
- Modal backdrop is separate (no blur)
- Blur intensity is static (not animated)
- Sheet border uses Colors.border (rgba(255,255,255,0.12))

**Remaining colour concerns (Phase 3D ⏳ — partially resolved):**
- ~~Date/time pills: cyan `#22D3EE` — should be `Colors.textSecondary`~~ ✅ Phase 2
- 8 style-level values migrated to semantic tokens (sheet bg, sheet border, closeBtn bg, venueText, distanceText, title, Ticket icon, ctaText) ✅ Phase 3D
- ~~Pill backgrounds: `rgba(255,255,255,0.05)` — retained~~ (5% opacity, no matching token)
- ~~Backdrop: `rgba(0, 0, 0, 0.6)` — acceptable, retained~~ (specific overlay alpha)
- **5 values still convertible but unmigrated:** 4 inline icon colors (closeBtn `0.7`, MapPin/Nav/Share `0.6`) should become `Colors.textSecondary`; `#A855F7` hypeText style should become `Colors.purple`
- **6 true technical exceptions remain** (see migration map §3D.2)

---

### SearchBar

| Field | Value |
|-------|-------|
| **File** | `components/fomo/search-bar.tsx` |
| **Export** | `SearchBar` (named) |
| **Props** | `onFilterChange?`, `isCalendarView?`, `onViewToggle?` |
| **Purpose** | **Discover-only** floating top bar: FOMO branding, local category filter panel, calendar/map toggle, notification bell |
| **Boundary** | Owns Discover's local controls only. No editable search input, no query state, no navigation launcher. |
| **Architecture** | Absolute positioned, safe-area-aware, `Animated.View` with mount animation |
| **Blur** | Experiment rejected and rolled back (see Phase 4 decision below) |
| **Fallback** | `Colors.surfaceGlass` on `inputContainer` — translucent solid surface, no native blur on Android |
| **Mount animation** | Fade + slide-down spring |
| **Focus animation** | Border colour interpolates from `Colors.borderGlass` to `Colors.borderFocus` |
| **Filter panel** | Animated maxHeight + opacity, category chips with active fill |
| **Category colours** | See DESIGN.md §2 — these are acceptable as restrained taxonomy colours |
| **Dependencies** | `Colors`, `Animated`, `TextInput` |

**Phase 4 status: Closed without SearchBar blur — rejected and rolled back.**

The experimental Android native-blur configuration was tested on a physical device and rejected because:

- no meaningful visual improvement was visible
- Expo SDK 54 Android native blur is experimental
- the experiment added implementation and performance risk without proven product value

**Final Android SearchBar implementation:**
- Translucent solid theme surface (`Colors.surfaceGlass`) with semantic resting/focus borders
- Existing focus animation (border colour interpolates from `borderGlass` to `borderFocus`)
- No native BlurView on Android
- No `experimentalBlurMethod` enabled
- All controls, spacing, and layout are unchanged — the search field and adjacent top buttons remain in their original positions with their original parents

**History:**
1. Wrapper-based attempt (rolled back) — introduced BlurView as layout wrapper around the search row, changing layout ownership, causing control overlap/misalignment
2. Absolute-layer repair (preserved layout) — one absolute-fill BlurView as decorative first child of `inputContainer`. No JSX element moved. But the Android native-blur experiment (step 3) was subsequently rolled back.
3. Android native-blur experiment (rejected) — `experimentalBlurMethod="dimezisBlurView"` with `intensity=40` and `blurReductionFactor=2` showed no meaningful benefit on physical device

**Premium visual quality on Android** comes from: surface hierarchy, translucent fills, subtle borders, restrained purple glow, clear active states, typography and spacing — not from native blur.

No BlurView exists on: filter panel, category chips, individual icon buttons, adjacent controls, event cards, list rows, CalendarView, or screen backgrounds.

---

### ExploreSearchInput

| Field | Value |
|-------|-------|
| **File** | `components/fomo/explore-search-input.tsx` |
| **Export** | `ExploreSearchInput` (named) |
| **Props** | `value: string`, `onChangeText: (text: string) => void`, `onClear: () => void` |
| **Purpose** | **Explore-only** editable search field. Screen-embedded — no floating layout, no BlurView. |
| **Architecture** | `View` (container, border animates on focus) → `Search` icon + `TextInput` + conditional `X` clear |
| **Dimensions** | Height 44px, border radius `Radii.lg`, border 1px, padding 12px |
| **Focus** | Border color switches from `Colors.borderGlass` to `Colors.borderFocus` on focus |
| **Boundary** | Owns visual input behavior only. Does not own debounce, networking, or filter state. |

---

### ExploreEventListItem

| Field | Value |
|-------|-------|
| **File** | `components/fomo/explore-event-list-item.tsx` |
| **Export** | `ExploreEventListItem` (memoized — `React.memo`) |
| **Props** | `event: ExploreEvent`, `onPress: (id: string) => void` |
| **Purpose** | **Explore-only** compact search-result cell. Opens existing `EventDetails` on tap. |
| **Architecture** | `TouchableOpacity` (static `style`, `activeOpacity: 0.65`) → 56×56 thumbnail (always present, FOMO fallback underneath) + content column |
| **Thumbnail** | 56×56, `borderRadius: 10`. Always renders. Real `Image` overlaid via `StyleSheet.absoluteFillObject`. FOMO fallback underneath with category-colored background + "FOMO" text. |
| **Content** | `flex: 1, minWidth: 0` — title (14px SemiBold, 2 lines) → date/time (11px, textMuted) → venue + category footer |
| **Cell** | `surfaceCard` bg, `borderSubtle` hairline border, 12px radius, 16px horizontal margin, 8px bottom margin, 10px internal padding, `flexDirection: 'row'` |
| **Boundary** | Must not be used outside Explore. No "View Details" child button, no per-row relationship requests, no inline Interested/Going. |
| **Image instrumentation** | Capped sample via `perfClaimImageSample()` (matches EventCard's pool). Only for real images — image-less rows never claim a sample. `onError` does not emit a success log. |
| **Dependencies** | `Colors.exploreCategory` (9 backend categories), `backendCategoryLabel`, perf helpers |

### FomoMap

| Field | Value |
|-------|-------|
| **File** | `components/fomo/fomo-map.tsx` |
| **Export** | `FomoMap` (named) |
| **Props** | `centerLat?`, `centerLng?`, `events?`, `selectedEventId?`, `showUserLocation?`, `onPinPress?`, `locateMe?` |
| **Purpose** | Mapbox map with event pins, camera animation, user location |
| **Architecture** | `@rnmapbox/maps` native module, dark-v11 style; Expo Go fallback (text placeholder) |
| **Pins** | `CircleLayer` on `ShapeSource` from GeoJSON — purple (`#A855F7`) with white stroke |
| **Selected pin** | Larger circle, `#BC13FE` (neon purple) with thick white stroke |
| **Camera** | `flyTo` for locate-me, `easeTo` for event selection, `none` for initial centering |
| **Dependencies** | `@rnmapbox/maps`, `Colors` |

---

### CalendarView

| Field | Value |
|-------|-------|
| **File** | `components/fomo/calendar-view.tsx` |
| **Export** | `CalendarView` (named) |
| **Props** | `events: Event[]`, `onEventPress: (event) => void` |
| **Purpose** | Date-strip + compact event list, replaces carousel in calendar mode |
| **Sub-components** | `DateStripPicker`, `CalendarEventCard` (internal) |
| **Blur** | `BlurView` on header (date strip area) |
| **Dependencies** | `BlurView`, `Animated`, `Colors` |

---

## Screen components (not reusable — `app/(tabs)/*`)

| Screen | File | Status | Data Source |
|--------|------|--------|-------------|
| `DiscoveryScreen` | `app/(tabs)/index.tsx` | ✅ Production | `useDiscovery` + `useEventRelationships` |
| `MyEventsScreen` | `app/(tabs)/saved.tsx` | ✅ Production | `useMyEvents` × 2 |
| `ProfileScreen` | `app/(tabs)/profile.tsx` | ✅ Production | `useAuth()` (background sync) |
| `SearchScreen` | `app/(tabs)/search.tsx` | ⏳ Placeholder (deferred to FOMO-172) | None |
| `LoginScreen` | `app/login.tsx` | ✅ Production | `useAuth()` |
| `TabsLayout` | `app/(tabs)/_layout.tsx` | ✅ Production | `expo-router` |
| `RootLayout` | `app/_layout.tsx` | ✅ Production | `AuthProvider` + font loader |

---

## Component dependency graph

```
RootLayout
  └─ AuthProvider
       └─ AuthGate
            └─ Stack
                 ├─ TabsLayout
                 │    └─ CustomTabBar (BlurView)
                 │
                 ├─ DiscoveryScreen             ← index.tsx
                 │    ├─ FomoMap                ← Mapbox / CircleLayer pins
                 │    ├─ SearchBar              ← Floating, category filters
                 │    ├─ FlatList
                 │    │    └─ EventCard[]       ← React.memo, LinearGradient CTA
                 │    ├─ CalendarView
                 │    │    └─ CalendarEventCard[]
                 │    └─ EventDetails           ← Modal + BlurView + IntentSelector
                 │         └─ IntentSelector
                 │
                 ├─ MyEventsScreen              ← saved.tsx
                 │    ├─ Tab Bar
                 │    ├─ ScrollView
                 │    │    └─ MyEventListItem[] ← React.memo
                 │    └─ EventDetails           ← shared component
                 │         └─ IntentSelector    ← shared component
                 │
                 ├─ ExploreScreen               ← search.tsx
                 │    ├─ ExploreSearchInput       ← editable search field
                 │    ├─ ExploreFilterModal       ← bottom sheet filters
                 │    ├─ FlatList
                 │    │    └─ ExploreEventListItem[] ← React.memo, branded cells
                 │    └─ EventDetails             ← Modal + BlurView + IntentSelector
                 │         └─ IntentSelector
                 │
                 ├─ ProfileScreen               ← profile.tsx
                 │    ├─ Avatar ring
                 │    ├─ Info rows
                 │    └─ FomoButton (logout)
                 │
                 ├─ ExploreScreen               ← search.tsx
                 │    ├─ ExploreSearchInput       ← editable search field
                 │    ├─ ExploreFilterModal       ← bottom sheet filters
                 │    ├─ FlatList
                 │    │    └─ ExploreEventListItem[] ← React.memo, branded cells
                 │    └─ EventDetails             ← Modal + BlurView + IntentSelector
                 │         └─ IntentSelector
                 │
                 └─ LoginScreen
                      └─ Auth buttons
```

---

## Theme dependency index

Every component that imports from `../../theme` (or `../../../theme`):

| Component | Imports from theme |
|-----------|-------------------|
| `EventCard` | `Colors`, `Gradients`, `Shadows` |
| `MyEventListItem` | `Colors`, `Radii`, `Spacing`, `Typography` |
| `IntentSelector` | `Colors`, `Radii`, `Typography` |
| `EventDetails` | `Colors`, `Gradients`, `Shadows` |
| `ExploreSearchInput` | `Colors`, `Radii`, `Spacing` |
| `ExploreEventListItem` | `Colors`, `Typography` |
| `SearchBar` | `Colors` |
| `FomoMap` | `Colors` |
| `CalendarView` | `Colors` |
| `FomoButton` | `Colors`, `Gradients`, `Radii`, `Spacing`, `Typography` |
| `FomoIconButton` | `Colors`, `Radii`, `Spacing` |
| `FomoErrorState` | `Colors`, `Radii`, `Spacing`, `Typography` |
| `FomoEmptyState` | `Colors`, `Radii`, `Spacing`, `Typography` |
| `FomoLoadingState` | `Colors` |
| `FomoScreen` | `Colors` |

No component imports `Colors.cyan` or `Colors.magenta` as of this audit (they are used in component-local config objects).
