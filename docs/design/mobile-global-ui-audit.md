# FOMO Mobile — Global UI Audit

> **Current-state audit of every screen in the mobile app.**
> Captured from disk: `apps/mobile/app/(tabs)/*`, `apps/mobile/app/login.tsx`, `apps/mobile/app/_layout.tsx`.
> No files modified — this is a read-only baseline.

---

## Screen inventory

### 1. Discover (`apps/mobile/app/(tabs)/index.tsx`)

**Status:** ✅ Production-ready, API-backed, performance-optimised

**Architecture:**
- `useDiscovery()` hook — single initial fetch, deferred until location resolves (FOMO-176 fix)
- `useDeviceLocation()` — GPS-permission-aware, falls back to defaults
- `useEventRelationships()` — batch intent sync for event IDs in view
- `FlatList` with horizontal carousel — FOMO-175: virtualized, `getItemLayout`, `windowSize=5`
- Unidirectional data: discovery → distance calculation → filtering → intents → render

**Data flow:**
1. Location resolves → `useDiscovery()` fires (one request, 289 ms median)
2. Events returned → distance computed via `haversineKm()`
3. Event IDs extracted → `useEventRelationships()` batch-fetches intents
4. Search/filter memoized over events + categories
5. `FlatList` renders via `renderEventCard` — memoized `EventCard`, stable `onPress`

**Cross-screen sync:** Revision-counter gating (FOMO-177): Discover mutations advance the revision counter; My Events reads it on focus and only refetches if counter changed.

**Visual concerns:**
- Date/time text uses `#22D3EE` (cyan) — should be `Colors.textSecondary`
- Price text uses `#22D3EE` (cyan) — should be `Colors.textPrimary` or removed
- No dedicated neon green for location/live state — uses `Colors.purple` for locate-me icon

**Verification note:** This is **not a placeholder**. It is a fully implemented, API-backed screen with measured performance baselines (FOMO-174 baseline document confirms 70 events, 289 ms median discovery request, FlatList virtualized).

---

### 2. My Events (`apps/mobile/app/(tabs)/saved.tsx`)

**Status:** ✅ Production-ready, API-backed, performance-optimised

**Architecture:**
- Two parallel `useMyEvents()` hooks — one per relationship type (interested/going)
- Independent fetch for each, loads in parallel
- `useFocusEffect` with revision-counter gating — only refetches on external invalidation
- `React.memo(MyEventListItem)` — stable `onPress`, stable event identity
- Local-intent application (FOMO-178): successful mutation updates local state directly, no refetch needed
- Date grouping: sections by Today/Tomorrow/future dates

**Data flow:**
1. Mount → both hooks fire independent `GET /me/events` requests (one per type)
2. Focus effect checks `getRelationshipRevision()` — refetches only if changed
3. Tab switch: Instant (data already loaded for both tabs)
4. Mutation: `setEventIntent()` → local state update → no network refetch

**Measured performance (FOMO-178):**
- Tab tap → stable list: 292 ms median (down from 500 ms in FOMO-174)
- Unchanged return: 0 requests, ~35 ms
- External invalidation: 2 requests, 268 ms to sync
- Mutation: +3 render passes (MyEventsScreen, EventDetails, IntentSelector) — no row re-render

**Visual concerns (P0 — see DESIGN.md §6):**
- Tab bar: "Interested" uses `Colors.magenta` — must be `Colors.purple`
- Tab bar: "Going" uses `Colors.success` — must be `Colors.neonGreen`
- Section label uses `Colors.purple` — ✅ correct
- Interested empty state icon uses `Colors.magenta` — should be `Colors.purple`

**Verification note:** This is **not a placeholder**. It is a fully implemented, API-backed screen with measured performance baselines. The `useMyEvents` hook (FOMO-178) handles initial loading, background refresh, and local optimistic updates with no redundant fetches.

---

### 3. Profile (`apps/mobile/app/(tabs)/profile.tsx`)

**Status:** ✅ Production-ready, auth-backed, FOMO-179 optimised

**Architecture:**
- Reads `user`, `isProfileLoading`, `profileError`, `retryProfileSync` from `useAuth()`
- No separate data fetch — profile is synchronised in background by `AuthProvider` (FOMO-179)
- `isProfileLoading` only shows spinner on first-ever load; never re-triggers on background refresh
- `retryProfileSync` allows manual retry after `profileError`
- Identity-change safe: `login()` clears `user` before starting new session; `sessionGenerationRef` guards stale responses

**Data flow:**
1. Auth bootstrap resolves → `beginUserSync()` fires in background
2. `GET /users/me` returns → `setUser()` renders profile fields
3. Tab mount: `isProfileLoading && !user` → `FomoLoadingState`
4. Once `user` loaded: renders avatar ring, username, email, role, member-since

**Visual elements:**
- Avatar ring: 80px circle, `Colors.purple` border at 40%, `Colors.purple` fill at 8%
- Username: Inter Bold 20px, `Colors.textPrimary`
- Email: Inter Regular 13px, `Colors.textSecondary`
- Divider: 1px `Colors.borderSubtle`
- Info rows: label `rgba(255,255,255,0.4)` / value `rgba(255,255,255,0.85)`

**Verification note:** This is **not a placeholder**. It is a fully implemented, auth-backed screen using the FOMO-179 background profile sync model. No dedicated data hook — the profile state is managed centrally by `AuthProvider`.

---

### 4. Search (`apps/mobile/app/(tabs)/search.tsx`)

**Status:** ⏳ Placeholder / not yet implemented

**Current content:**
```tsx
<FomoEmptyState
  icon={<Search size={48} color={Colors.purple} strokeWidth={1.2} />}
  message="Search is coming soon"
  sub="Browse events from the Discover tab for now."
/>
```

**Assessment:** This is the **only** placeholder screen. The tab renders a static empty state with no data fetching, no input, and no search functionality. It exists as a route placeholder for the tab bar.

**Scope (deferred to FOMO-172):** This design task may define the visual treatment of the Search screen (layout chrome, search bar styling, empty/focused states) but must NOT invent search behaviour, add mock recent searches, add fake trending events, add hard-coded search results, or implement FOMO-172. All functional search work belongs to FOMO-172.

---

### 5. Login (`apps/mobile/app/login.tsx`)

**Status:** ✅ Production-ready, auth-backed

**Architecture:**
- Reads `isLoading`, `login`, `authError` from `useAuth()`
- Two auth paths: Google IdP (primary) and email/password (fallback via Keycloak realm login)
- Local `isLoggingIn` state for button feedback during the OAuth redirect

**Visual elements:**
- Logo ring: 96px circle, purple border at 60%, purple fill at 10%, "F" letter
- App name: "FOMO" in Inter ExtraBold 36px, 6px letter-spacing
- Tagline: "Find out, don't miss out."
- Google button: white (#fff), Google-blue "G" icon
- Email link: subdued `Colors.textMuted`, underlined

---

### 6. Auth callback (`apps/mobile/app/auth/callback.tsx`)

**Status:** ✅ Production-ready, minimal route

- 616 bytes: Receives Keycloak OAuth redirect, passes through to Expo AuthSession
- No UI — runs the token-exchange and navigates to the tabs

---

## Cross-cutting concerns

### Navigation (`apps/mobile/app/(tabs)/_layout.tsx`)

**Tab bar:** Custom `CustomTabBar` component:
- `BlurView intensity={20}` with dark tint
- Pill shape: `borderRadius: 16`, border `rgba(255,255,255,0.12)`, fallback bg `rgba(12,12,18,0.88)`
- Active tab: icon/label `#A855F7` (purple), `activeBg` at 20% purple fill
- Inactive tab: `rgba(255,255,255,0.45)`
- Measured: tab navigation 45–90 ms

**Concern:** Active colour `#A855F7` — should use `Colors.purple` theme token (currently matches, but should reference the token). No dedicated neon-green active state — intentional, only one accent at a time.

### Root layout (`apps/mobile/app/_layout.tsx`)

- `AuthProvider` wraps all children
- `AuthGate` blocks protected routes until token resolved
- Font loading (Inter weights) gates splash screen
- `StatusBar style="light"` throughout

---

## UI primitive audit

| Primitive | File | Notes |
|-----------|------|-------|
| `FomoScreen` | `components/ui/FomoScreen.tsx` | Dark container, `flex:1`, `bg:#0B0B0F` |
| `FomoButton` | `components/ui/FomoButton.tsx` | 3 variants: primary (neon gradient), ghost (glass border), danger (red) |
| `FomoIconButton` | `components/ui/FomoIconButton.tsx` | Glass-style, active highlight, 2 sizes |
| `FomoLoadingState` | `components/ui/FomoLoadingState.tsx` | Centered `ActivityIndicator`, defaults to `Colors.purple` |
| `FomoErrorState` | `components/ui/FomoErrorState.tsx` | Error icon + message + optional retry button |
| `FomoEmptyState` | `components/ui/FomoEmptyState.tsx` | Icon + message + optional sub + optional action |

---

## Colour consistency issues (all screens)

| Issue | Current | Must be | Locations |
|-------|---------|---------|-----------|
| No `neonGreen` token | Missing from `theme/index.ts` | Add `#39FF88` | Theme |
| "Interested" uses magenta | `Colors.magenta` | `Colors.purple` | `saved.tsx`, `IntentSelector.tsx`, `MyEventListItem.tsx` |
| "Going" uses cyan | `Colors.cyan` | `Colors.neonGreen` | `IntentSelector.tsx` |
| "Going" tab uses success green | `Colors.success` | `Colors.neonGreen` | `saved.tsx` tab bar |
| Date/time in cyan | `#22D3EE` | `Colors.textSecondary` | `event-card.tsx`, `event-details.tsx` |
| Price in cyan | `#22D3EE` | Remove or `Colors.textPrimary` | `event-card.tsx` |
| Pill background date/time | `#22D3EE` | `Colors.textSecondary` | `event-details.tsx` |
| Calendar toggle active cyan | `#22D3EE` | Keep (Festival category) | `search-bar.tsx` — ✅ permitted |

---

## Blur placement audit

> **Do not remove expo-blur globally.** Blur is part of the identity. The rules below limit blur to elevated surfaces; repeated/virtualised items use translucent solid fills.
> **Android:** Always pair BlurView with a translucent solid fallback (`Colors.surfaceGlass`) — blur rendering varies by device hardware.

| Element | Current | Should have blur? | Verdict |
|---------|---------|-------------------|---------|
| Search bar | `Colors.surfaceGlass` | ✅ Yes (per DESIGN.md) | ✅ Correct |
| Navigation pill | `BlurView intensity=20` | ✅ Yes | ✅ Correct |
| Event details sheet | `BlurView intensity=20` | ✅ Yes | ✅ Correct |
| Locate-me button | Translucent fill | ✅ Yes | ⚠️ Should add `BlurView` with solid fallback |
| Event cards | `Colors.surfaceCard` | ❌ No | ✅ Correct |
| My Events rows | `Colors.surfaceCard` | ❌ No | ✅ Correct |
| Category chips | Translucent fill | ❌ No | ✅ Correct |
| Loading/error/empty states | Solid `Colors.background` | ❌ No | ✅ Correct |
