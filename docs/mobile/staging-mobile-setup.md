# Mobile App: Staging Setup

> FOMO-167 — bootstrap mobile app against staging services.

> **Canonical workflow lives elsewhere:** for toolchain setup, building,
> installing, and the daily development loop, follow
> [local-android-development.md](./local-android-development.md). This
> document owns **staging-specific service URLs and environment values**.
> The feature-state tables below are a historical snapshot from the
> FOMO-167/168/169 era; auth (FOMO-170), saved/interested/going (FOMO-171)
> and Explore search (FOMO-172) have shipped since.

## Required Environment Variables

Copy `apps/mobile/.env.example` to `apps/mobile/.env` and fill in the values below.

| Variable | Staging Value | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `https://api.staging.fomo-lab.org` | Backend REST API base URL |
| `EXPO_PUBLIC_AUTH_URL` | `https://auth.staging.fomo-lab.org` | Keycloak base URL |
| `EXPO_PUBLIC_KEYCLOAK_REALM` | `fomo-users` | End-user realm — **not** `fomo-admin` |
| `EXPO_PUBLIC_KEYCLOAK_CLIENT_ID` | `fomo-mobile` | Public PKCE client |
| `EXPO_PUBLIC_AUTH_REDIRECT_SCHEME` | `fomo` | Must match `scheme` in `app.json` |
| `EXPO_PUBLIC_MAPBOX_TOKEN` | `pk.…` | Mapbox **public** token; get from Mapbox dashboard |
| `EXPO_PUBLIC_DEFAULT_LAT` | `37.9838` | Default discovery latitude (Athens) |
| `EXPO_PUBLIC_DEFAULT_LNG` | `23.7275` | Default discovery longitude (Athens) |
| `EXPO_PUBLIC_DEFAULT_RADIUS_KM` | `50` | Discovery radius in km |

> **Why Athens defaults?** Current staging events are sourced from Greece via More.com.
> Change these coordinates to match your city when running locally.
> These vars are temporary and will be superseded once `expo-location` + device
> permission flow is implemented.

> **Warning:** `apps/mobile/.env` must contain a `pk.*` Mapbox token, not a `sk.*` secret token.
> The `sk.*` secret token for downloading the native Mapbox SDK belongs in
> `~/.gradle/gradle.properties` as `MAPBOX_DOWNLOADS_TOKEN=sk.…`.

## Running on a Physical Android Phone

### Prerequisites

- Android phone with USB debugging enabled
- ADB installed (`adb devices` should list your phone)
- Node 20+, pnpm, **JDK 21 via `JAVA_HOME`** (see the
  [canonical runbook](./local-android-development.md) for toolchain setup)
- Mapbox `sk.*` token in `~/.gradle/gradle.properties` (see the runbook's
  Mapbox section — requirement is inconclusive when the Gradle cache is warm)

### First-time build (required — Expo Go cannot run this app)

```bash
# From the monorepo root
cd apps/mobile
pnpm expo run:android
```

This compiles the native Android APK and installs it on the connected device.
Subsequent changes to JS/TS only need Metro — the native build is reused.

### Metro + adb reverse (subsequent runs)

```bash
# Forward Metro port from phone to your machine
adb reverse tcp:8081 tcp:8081

# Start Metro bundler (from monorepo root)
pnpm --filter @fomo/mobile start
```

Then open the FOMO app on the phone — it will connect to Metro over the USB tunnel.

### Using a staging `.env`

```bash
# apps/mobile/.env
EXPO_PUBLIC_API_URL=https://api.staging.fomo-lab.org
EXPO_PUBLIC_AUTH_URL=https://auth.staging.fomo-lab.org
EXPO_PUBLIC_MAPBOX_TOKEN=pk.YOUR_TOKEN_HERE
EXPO_PUBLIC_DEFAULT_LAT=37.9838
EXPO_PUBLIC_DEFAULT_LNG=23.7275
EXPO_PUBLIC_DEFAULT_RADIUS_KM=50
```

After editing `.env`, restart Metro with cache clear:

```bash
pnpm --filter @fomo/mobile start:clear
```

## Staging URLs

| Service | URL |
|---|---|
| API | `https://api.staging.fomo-lab.org` |
| Auth / Keycloak | `https://auth.staging.fomo-lab.org` |
| Dashboard | `https://dashboard.staging.fomo-lab.org` |

## Expo Go vs Dev Build

| Feature | Expo Go | Dev Build |
|---|---|---|
| JS / React Native screens | ✅ | ✅ |
| NativeWind / Tailwind | ✅ | ✅ |
| Mapbox map | ❌ (native module) | ✅ |
| expo-location | ❌ (native module) | ✅ |

**Conclusion: a dev build is required.** Expo Go additionally cannot complete
the `fomo://` authentication redirect, and the app is login-gated since
FOMO-170 — so Expo Go is not a supported workflow at all (see the
[canonical runbook](./local-android-development.md)).

## Event Detail Screen (FOMO-169)

### Route

`/event/[id]` — a Stack screen pushed on top of the Discover tab. Reachable from:

- **Event card** (carousel, map view) — direct navigation to detail screen
- **Calendar list item** — direct navigation to detail screen
- **Map pin bottom-sheet** — via "Full Details →" link in the action row

### Backend

`GET /api/v1/events/{event_id}` — returns `EventDiscoveryResponse` (same schema as discovery).
Public endpoint (no auth required). Returns 404 if event is not live/public.

### Fields on detail screen

| Field | Source | Notes |
|---|---|---|
| Title | `title` | Always shown |
| Hero image | `photo_url` | Shown when present; dark gradient placeholder when absent |
| Category badge | `category` | Colored border/text per category |
| High Hype badge | `hype_score ≥ 70` | Only shown when truly high |
| Venue | `location_name` | "TBA" fallback |
| Distance | computed (Haversine) | Shown when device location granted |
| Date | `start_time` formatted | |
| Time | `start_time` formatted | |
| Directions | `lat/lng` | Hidden when coordinates invalid/missing |
| Share | `title + source_url` | Native share sheet |
| Source domain | `source_url` | Extracted hostname (e.g. "more.com") |
| Get Tickets | `ticket_url` | Hidden when absent |
| View Source | `source_url` | Fallback CTA when no ticket_url |

### Fields intentionally absent

| Field | Why |
|---|---|
| Description | No `description` field in `EventDiscoveryResponse` — deferred |
| Attendee count | No API field |
| Price | No API field |
| End time | Not mapped in `UiEvent`; shown as follow-up when needed |
| Save/Interested/Going | Requires auth — deferred |
| Comments/social | Deferred |

### Navigation

- Back button (top-left, always visible)
- Share button (top-right in hero area)
- Android hardware back works via Stack

---

## What Discover V1 + FOMO-168 Map/Location Foundation Supports

On boot the Discover tab:
1. Requests foreground location permission via `expo-location`
2. If **granted**: uses real device coordinates for discovery API and map camera
3. If **denied/unavailable**: falls back to `EXPO_PUBLIC_DEFAULT_LAT/LNG` (Athens for staging)

Discovery endpoint:
```
GET /api/v1/events/discovery?lat=<LAT>&lng=<LNG>&radius_km=<RADIUS>
```
Coordinates come from `useDeviceLocation` (real or default). The map camera always uses the same origin. Distance from origin is computed client-side (Haversine) and shown on cards/detail sheets.

| Feature | Status | Notes |
|---|---|---|
| Event card carousel (map view) | ✅ Real data | Tapping navigates to full detail screen |
| Calendar date strip + event list | ✅ Real data | Tapping navigates to full detail screen |
| Event detail screen | ✅ FOMO-169 | Full-screen route `/event/[id]`; fetches from `GET /api/v1/events/{id}` |
| Map pin → bottom sheet preview | ✅ Real data | "Full Details →" link opens detail screen |
| "Get Tickets" / "View Source" CTA | ✅ Real | Opens `ticket_url ?? source_url` in browser; hidden when absent |
| Share button | ✅ Real | Native share sheet with event title + source URL |
| Directions | ✅ Real | `maps/dir/?destination=<lat>,<lng>`; hidden when coords missing/invalid |
| Text search | ✅ Client-side | Filters loaded events by title or venue name |
| Category chips | ✅ Client-side | Filters events by real API category |
| Loading / error / empty states | ✅ | Spinner, retry button, contextual messages |
| Device location permission | ✅ FOMO-168 | Foreground permission request on first open |
| Location fallback | ✅ FOMO-168 | Falls back to env defaults when denied/unavailable |
| Map camera | ✅ FOMO-168 | Follows device location (or default); animates to selected event |
| Event pins on map | ✅ FOMO-168 | Purple circle per event with valid coordinates; tappable |
| Pin tap → event selection | ✅ FOMO-168 | Tapping a pin selects event; syncs carousel + detail sheet |
| Selected event pin | ✅ FOMO-168 | Magenta highlight; camera eases to event |
| User location dot | ✅ FOMO-168 | Mapbox native blue dot; only shown when permission granted |
| Distance computation | ✅ FOMO-168 | Haversine km from origin; shown on cards when available |
| Locate-me button | ✅ FOMO-168 | Floating button; flies camera to current location; re-requests permission if denied |
| Map pin clustering | ❌ Deferred | Future task |
| Map-area search / pan-to-load | ❌ Deferred | Future task |
| City/date explore search | ❌ Deferred | FOMO-172/FOMO-174: "show events in Thessaloniki next Friday" type queries |
| Search results list | ❌ Deferred | FOMO-172: real-time search with server-side query |
| Auth / saved events / profile | ❌ Deferred | Requires OIDC flow |
| Heart / Save action | ❌ Deferred | Requires auth + backend endpoint |
| Attendee count | ❌ Not shown | No API field |
| Price | ❌ Not shown | No API field |
| FOMO-owned deep links | ❌ Deferred | Share currently uses raw source URL; app-owned event URLs TBD |

## Location Permission Behavior

| State | Discovery coords | Map camera | User dot | Distance |
|---|---|---|---|---|
| `pending` | default (env) | default | hidden | from default origin |
| `granted` | real device | real device → refetches | shown | from device |
| `denied` | default (env) | default | hidden | from default origin |
| `unavailable` / `error` | default (env) | default | hidden | from default origin |

The permission dialog appears on **first launch** (or when "Never ask again" was not selected). The app remains fully usable in all states — denial just means Athens-default discovery.

**Note on re-prompting**: Android caches the permission decision. If permission was previously granted, `requestForegroundPermissionsAsync` returns immediately without a dialog. If denied with "ask again" possible, the locate-me button re-prompts. If "Never ask again" was selected, the locate button will not show a dialog; the user must grant permission in Android Settings manually.

## Locate-Me Button

A circular floating button sits **top-right** inside the map, just below the SearchBar (map view only).

| State | Icon | Tapping does |
|---|---|---|
| `granted` | Purple `#A855F7` | Fly camera to real device coords immediately |
| `denied` / `unavailable` / `error` | Dim white | Request permission; fly to real coords once granted |
| `pending` / awaiting grant | Spinner | No-op while request in flight |

**Locate Me flyTo is deferred**: if permission is not yet granted when the button is tapped,
the camera does **not** fly to the default/Athens coords. Instead a `pendingLocate` flag is
set and the flyTo fires only after `locationStatus` transitions to `'granted'` with real coords.

## Location Mode Indicator

A small non-intrusive pill sits **bottom-left above the carousel** (map view only, hidden while pending).

| Text | Meaning |
|---|---|
| `· Your location` (purple dot) | Real device GPS in use |
| `· Default location` (dim dot) | Fallback coords (env defaults) active |

## Map Pins Behavior

- Only real events from the discovery API render as pins — no decorative or mock markers
- One purple circle (`#A855F7`, r=8) per event with valid, non-null-island coordinates
- Tapping a pin selects the event: syncs the carousel and opens the detail sheet
- Selected event: larger magenta circle (`#BC13FE`, r=12) on a separate top layer; also tappable
- No clustering in this iteration (future task)

## Directions Behavior

Opens `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`.

- Uses the device's current location as origin in Google Maps (no origin parameter needed)
- Hidden when event has no valid coordinates
- Not routed turn-by-turn from our app — Google Maps handles routing from device location

## Intentionally Hidden / Deferred UI

- **Attendees count**: removed — the API has no attendee data.
- **Heart/Save button**: removed — no backend endpoint or auth yet.
- **"High Hype" badge**: only shown when `hype_score ≥ 70`. Most ingested events have score 0 — correct behaviour.
- **Price**: not shown — no price field on `EventDiscoveryResponse`.
- **Card label**: "View Tickets" → "View Details" — the card CTA opens the detail sheet, not a ticket URL.
- **NeonGrid / decorative overlay**: removed. The Mapbox dark map is the visual backdrop. The neon road grid and fake pulsing marker dots that existed as decorative UI in earlier iterations are gone. Only real API event pins appear on the map.
- **Map pin clustering**: deferred. Events render individually; high-density areas will overlap.
- **Map-area search / pan-to-load**: deferred. Discovery only fetches once per origin; panning the map does not trigger a new query.
- **City/date explore search**: deferred to FOMO-172/FOMO-174. "Show me events in Thessaloniki next Friday" type queries require a separate search flow.
- **Share**: uses `ticket_url ?? source_url` as the share URL. Once FOMO-owned public event detail pages exist, Share should use those app-owned URLs instead of raw scraper sources.
- **Search results list**: the current search input filters the already-loaded carousel in-place. A real-time query against the API with a results list belongs to FOMO-172 Mobile Search and Filters.

## Known Limitations

| # | Limitation | Follow-up |
|---|---|---|
| 1 | Staging events are in Athens; if device location is in another city, events list will be empty | Use env defaults or grant permission while in Athens |
| 2 | Directions uses device location as Google Maps origin, but app has no turn-by-turn routing | Future: compute route from device coords in-app |
| 3 | Map pins do not cluster — overlapping events in dense areas are hard to tap | Future clustering task |
| 4 | Map-area panning does not refetch events for new area | Future: pan-to-load |
| 5 | ~~No auth wiring~~ **Resolved** — Keycloak PKCE auth shipped in FOMO-170 | See [mobile-auth-keycloak.md](./mobile-auth-keycloak.md) |
| 6 | Mapbox token in `.env` should be `pk.*` not `sk.*` | Replace in local `.env`; never commit |
| 7 | ~~Search/Saved/Profile tabs are stub screens~~ **Resolved** — Explore search (FOMO-172), Saved (FOMO-171), Profile (FOMO-170) shipped | — |
| 8 | No pagination on discovery endpoint | Backend + mobile work required |
| 9 | Calendar date matching uses local timezone — UTC events near midnight may appear on wrong date | Fix date parsing to use UTC display |

## Troubleshooting

**Metro can't connect to phone**
```bash
adb reverse tcp:8081 tcp:8081
```

**Build fails — Mapbox native modules missing**
Ensure `~/.gradle/gradle.properties` contains:
```
MAPBOX_DOWNLOADS_TOKEN=sk.YOUR_SECRET_TOKEN
```

**API calls fail (CORS or SSL)**
Check that `EXPO_PUBLIC_API_URL` in `.env` exactly matches the staging URL (no trailing slash).

**Map shows dark placeholder**
Either Expo Go is being used (expected) or `EXPO_PUBLIC_MAPBOX_TOKEN` is empty or invalid.

**Empty event list on staging**
The staging DB may have no events with `status=live` near the default coordinates.
Staging defaults to Athens (37.9838, 23.7275) — verify that approved events exist there
in the moderation dashboard, or adjust `EXPO_PUBLIC_DEFAULT_LAT/LNG` in `.env`.
