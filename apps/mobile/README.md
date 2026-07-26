# FOMO Mobile (`@fomo/mobile`)

The FOMO event-discovery mobile app: Expo SDK 54 / React Native 0.81.5, with
Mapbox maps, Keycloak (PKCE) authentication, and the Discover/Explore/Saved/
Profile experience.

**Platforms:** FOMO is a cross-platform Android + iOS product. **Android is
the active MVP target** (physical acceptance device: OnePlus 12). iOS native
development starts after the Android MVP — there is no `ios/` project yet.

> ⛔ `apps/mobile/android/` is committed, hand-maintained native source.
> **Never run `expo prebuild` / `expo prebuild --clean`** — it would destroy
> required manual fixes. Expo Go is not a supported development environment.

## Documentation

| Need | Document |
|---|---|
| **Set up & develop (canonical runbook)** | [docs/mobile/local-android-development.md](../../docs/mobile/local-android-development.md) |
| Troubleshooting & recovery | [docs/mobile/android-expo-debugging-guide.md](../../docs/mobile/android-expo-debugging-guide.md) |
| Staging services & env values | [docs/mobile/staging-mobile-setup.md](../../docs/mobile/staging-mobile-setup.md) |
| Authentication (Keycloak) | [docs/mobile/mobile-auth-keycloak.md](../../docs/mobile/mobile-auth-keycloak.md) |
| Performance methodology | [docs/mobile/mobile-performance-baseline.md](../../docs/mobile/mobile-performance-baseline.md) |

## Common commands (from the monorepo root)

| Command | Purpose |
|---|---|
| `pnpm --filter @fomo/mobile start` | Start Metro dev server |
| `pnpm --filter @fomo/mobile start:clear` | Metro with cleared cache (after `.env` changes) |
| `pnpm --filter @fomo/mobile android` | Build + install the Android debug app (`expo run:android`) |
| `pnpm --filter @fomo/mobile lint` | ESLint |
| `pnpm --filter @fomo/mobile exec tsc --noEmit` | TypeScript check (no dedicated script yet) |

Physical devices additionally need `adb reverse tcp:8081 tcp:8081` — see the
runbook for the full workflow.
