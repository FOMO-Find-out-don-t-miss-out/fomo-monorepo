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
| **Ghost** | 1px border, transparent bg, white secondary text |
| **Danger** | Ghost variant with `Colors.error` border/text |
| **Memoized** | No (low render frequency per screen) |
| **Dependencies** | `Colors`, `Gradients`, `Radii`, `Spacing`, `Typography` |

---

### FomoIconButton

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoIconButton.tsx` |
| **Export** | `FomoIconButton` (named) |
| **Props** | `icon`, `onPress?`, `active?`, `activeColor? (default Colors.purple)`, `disabled?`, `size? ('sm'\|'md')`, `style?`, `accessibilityLabel?` |
| **Purpose** | Glass-style icon button for action rows, toggle states |
| **Style** | `borderColor: activeColor@40%` when active, `Colors.borderGlass` otherwise; `surfaceGlass` bg when active |
| **Memoized** | No |

---

### FomoLoadingState

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoLoadingState.tsx` |
| **Export** | `FomoLoadingState` (named) |
| **Props** | `color? (default Colors.purple)`, `style?` |
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
| **Retry style** | Purple border pill at 40% opacity, purple dim background on press |
| **Dependencies** | `Colors.error`, `Colors.purple`, `Colors.purpleDim` |

---

### FomoEmptyState

| Field | Value |
|-------|-------|
| **File** | `components/ui/FomoEmptyState.tsx` |
| **Export** | `FomoEmptyState` (named) |
| **Props** | `icon`, `message`, `sub?`, `action? ({label, onPress})`, `style?` |
| **Purpose** | Centered empty state with icon, heading, optional sub + action |
| **Action style** | Purple border pill at 40% opacity, purple dim on press |
| **Dependencies** | `Colors.purple`, `Colors.purpleDim` |

---

## Feature components (`components/fomo/`)

### EventCard

| Field | Value |
|-------|-------|
| **File** | `components/fomo/event-card.tsx` |
| **Export** | `EventCard` (memoized) |
| **Props** | `event: Event`, `isActive?`, `onPress?: (id: string) => void` |
| **Purpose** | Discover carousel card: image, category badge, title, venue, date/time, CTA |
| **Architecture** | `Animated.View` (shadow/scale/transform) → `Pressable` (bg/clip/padding) → content |
| **Memoized** | `React.memo` — FOMO-175: stable `onPress` + stable event identity |
| **Press animation** | Spring scale 1→0.97 on press-in, 0.97→1 on press-out |
| **Image loading** | Sampled timing via `perfClaimImageSample` (capped at 6 per session) |
| **Dimensions** | 260×180px, border-radius 16px |
| **Cover image** | `ImageBackground` with `StyleSheet.absoluteFill` |
| **CTA** | `LinearGradient` (`#BC13FE`→`#9333EA`), "View Details" |
| **Styling pattern** | Theme tokens and hardcoded values mixed — **see concerns below** |
| **Dependencies** | `Colors`, `Gradients`, `Shadows`, `LinearGradient`, `ImageBackground` |

**Hardcoded colour concerns:**
- Date row: `#22D3EE` (cyan) for date/time text — use `Colors.textSecondary`
- Price: `#22D3EE` (cyan) for price — use `Colors.textPrimary`
- Venue: `rgba(255,255,255,0.5)` — should use `Colors.textSecondary`
- Distance: `rgba(255,255,255,0.35)` — should use `Colors.textMuted`
- CTA border: `rgba(188, 19, 254, 0.3)` — should reference theme border token

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

**Colour concerns:**
- Intent dot: `Colors.magenta` for interested — must be `Colors.purple`
- Intent dot: `Colors.success` for going — must be `Colors.neonGreen`
- Time: `#22D3EE` — should be `Colors.textSecondary`

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
| **Blur** | `BlurView intensity=20` dark tint on entire sheet |
| **CTA** | `LinearGradient` (`#BC13FE`→`#9333EA`), `Shadows.ctaGlow` applied |
| **Actions** | Directions (Google Maps deep link), Share |
| **Dependencies** | `BlurView`, `LinearGradient`, `Modal`, `Linking`, `Share` |

**Colour concerns:**
- Date/time pills: cyan `#22D3EE` — should be `Colors.textSecondary`
- Pill backgrounds: `rgba(255,255,255,0.05)` — should reference `Colors.surfaceCard` or similar
- Backdrop: `rgba(0, 0, 0, 0.6)` — acceptable, no change needed

---

### SearchBar

| Field | Value |
|-------|-------|
| **File** | `components/fomo/search-bar.tsx` |
| **Export** | `SearchBar` (named) |
| **Props** | `onFilterChange?`, `onSearchChange?`, `isCalendarView?`, `onViewToggle?` |
| **Purpose** | Floating top search bar with animated focus border, category filter panel, view toggle, bell |
| **Architecture** | Absolute positioned, safe-area-aware, `Animated.View` with mount animation |
| **Blur** | `Colors.surfaceGlass` (translucent, not explicit BlurView — uses rgba background, not blur) |
| **Mount animation** | Fade + slide-down spring |
| **Focus animation** | Border colour interpolates from `Colors.borderGlass` to `Colors.borderFocus` |
| **Filter panel** | Animated maxHeight + opacity, category chips with active fill |
| **Category colours** | See DESIGN.md §2 — these are acceptable as restrained taxonomy colours |
| **Dependencies** | `Colors`, `Animated`, `TextInput` |

**Note:** The search bar currently uses `Colors.surfaceGlass` (translucent rgba) rather than an explicit `BlurView`. According to DESIGN.md §4, the floating search bar should use real blur. This is a P2 enhancement: wrap the container in a `BlurView` for true frosted-glass effect with an Android-safe solid fallback (`Colors.surfaceGlass` as `backgroundColor`).

---

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
                 ├─ ProfileScreen               ← profile.tsx
                 │    ├─ Avatar ring
                 │    ├─ Info rows
                 │    └─ FomoButton (logout)
                 │
                 ├─ SearchScreen                ← placeholder
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
