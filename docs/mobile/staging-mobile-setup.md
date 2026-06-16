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

## What the App Does on Staging

On boot the Discover tab calls:
```
GET /api/v1/events/discovery?lat=<LAT>&lng=<LNG>&radius_km=<RADIUS>
```
Coordinates are read from `EXPO_PUBLIC_DEFAULT_LAT/LNG/RADIUS_KM` at Metro bundle time
via `apps/mobile/utils/location-config.ts`. The map initial camera uses the **same values**,
so the map and the API query always point to the same city.
Staging defaults to central Athens (37.9838, 23.7275, 50 km) where current events live.
Device location permission is a follow-up (see Known Limitations).

- Loading: spinner in the card carousel area
- Events found: horizontal scroll carousel of event cards
- Empty: "No events nearby" message
- Error: "Could not load events" + Retry button

## Known Limitations

| # | Limitation | Follow-up |
|---|---|---|
| 1 | Discovery uses configurable env-var coords (Athens default) — not real device location | Add `expo-location` + permission flow |
| 2 | `EventDiscoveryResponse` has no `category` or `hype_score` | Extend backend schema in domain layer |
| 3 | All events show category "Music" | Blocked on #2 |
| 4 | No auth wiring | FOMO-147/151 patterns can be ported from dashboard |
| 5 | Mapbox token in `.env` is currently `sk.*` (wrong) | Replace with `pk.*` token from Mapbox dashboard |
| 6 | Search, Saved, Profile tabs are placeholder screens | Future iterations |
| 7 | No pagination on discovery endpoint | Backend + mobile work required |

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
