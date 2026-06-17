# Mobile App: Staging Setup

> FOMO-167 — bootstrap mobile app against staging services.

## Required Environment Variables

Copy `apps/mobile/.env.example` to `apps/mobile/.env` and fill in the values below.

| Variable | Staging Value | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `https://api.staging.fomo-lab.org` | Backend REST API base URL |
| `EXPO_PUBLIC_AUTH_URL` | `https://auth.staging.fomo-lab.org` | Keycloak — reserved for future OIDC integration |
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
- Node 20+, pnpm, Java 17+
- Mapbox `sk.*` token in `~/.gradle/gradle.properties` (required for first native build)

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

**Conclusion: a dev build is required.** Expo Go will render a dark placeholder instead of the Mapbox map but all other screens (Search, Saved, Profile) and the event carousel work.

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
| Event card carousel (map view) | ✅ Real data | Title, venue, date/time, category, cover image, distance |
| Calendar date strip + event list | ✅ Real data | Filtered by selected date |
| Event details bottom sheet | ✅ Real data | Category badge, hype badge (when score ≥ 70), distance |
| "Get Tickets" / "View Source" CTA | ✅ Real | Opens `ticket_url ?? source_url` in browser; hidden when absent |
| Share button | ✅ Real | Native share sheet with event title + source URL |
| Directions | ✅ Real | `maps/dir/?destination=<lat>,<lng>`; hidden when coords missing/invalid |
| Text search | ✅ Client-side | Filters loaded events by title or venue name |
| Category chips | ✅ Client-side | Filters events by real API category |
| Loading / error / empty states | ✅ | Spinner, retry button, contextual messages |
| Device location permission | ✅ FOMO-168 | Foreground permission request on first open |
| Location fallback | ✅ FOMO-168 | Falls back to env defaults when denied/unavailable |
| Map camera | ✅ FOMO-168 | Follows device location (or default); animates to selected event |
| Event pins on map | ✅ FOMO-168 | Purple circle per event with valid coordinates |
| Selected event pin | ✅ FOMO-168 | Magenta highlight; camera zooms to event |
| User location dot | ✅ FOMO-168 | Mapbox native blue dot; only shown when permission granted |
| Distance computation | ✅ FOMO-168 | Haversine km from origin; shown on cards when available |
| Map pin clustering | ❌ Deferred | Future task |
| Map-area search / pan-to-load | ❌ Deferred | Future task |
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

The permission dialog appears on **first launch** only. The app remains fully usable in all states — denial just means Athens-default discovery until the user grants permission.

## Map Pins Behavior

- One purple circle (`#A855F7`) per event with valid lat/lng
- Events with missing, NaN, or both-zero coordinates get no pin
- Selected event gets a larger magenta circle (`#BC13FE`) on a separate layer (renders on top)
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
- **Map pin clustering**: deferred. Events render individually; high-density areas will overlap.
- **Map-area search / pan-to-load**: deferred. Discovery only fetches once per origin; panning the map does not trigger a new query.
- **Share**: uses `ticket_url ?? source_url` as the share URL. Once FOMO-owned public event detail pages exist, Share should use those app-owned URLs instead of raw scraper sources.
- **Search results list**: the current search input filters the already-loaded carousel in-place. A real-time query against the API with a results list belongs to FOMO-172 Mobile Search and Filters.

## Known Limitations

| # | Limitation | Follow-up |
|---|---|---|
| 1 | Staging events are in Athens; if device location is in another city, events list will be empty | Use env defaults or grant permission while in Athens |
| 2 | Directions uses device location as Google Maps origin, but app has no turn-by-turn routing | Future: compute route from device coords in-app |
| 3 | Map pins do not cluster — overlapping events in dense areas are hard to tap | Future clustering task |
| 4 | Map-area panning does not refetch events for new area | Future: pan-to-load |
| 5 | No auth wiring | Port FOMO-147/151 patterns from dashboard |
| 6 | Mapbox token in `.env` should be `pk.*` not `sk.*` | Replace in local `.env`; never commit |
| 7 | Search/Saved/Profile tabs are stub screens | Future iterations |
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
