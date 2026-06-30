# Android + Expo Debugging Guide

For FOMO mobile developers working on the React Native Android dev build.

---

## Prerequisites

- **Node 20+** — check with `node --version`
- **pnpm** — `pnpm --version`
- **Java 17** — `java -version` (Gradle requires exactly Java 17)
- **Android SDK** — installed via Android Studio or standalone CLI tools
  - Set `ANDROID_HOME` env var: `%LOCALAPPDATA%\Android\Sdk` (Windows)
- **ADB (Android Debug Bridge)** — comes with the Android SDK; ensure it's on your `PATH`
- **Physical Android device** OR an emulator (AVD in Android Studio)
- **Mapbox `sk.*` token** in `~/.gradle/gradle.properties`:
  ```
  MAPBOX_DOWNLOADS_TOKEN=sk.your-secret-token-here
  ```

---

## Device Setup

### Enable USB Debugging on Android

1. Open **Settings → About phone**
2. Tap **Build number** 7 times to unlock Developer Options
3. Go to **Settings → Developer Options**
4. Enable **USB debugging**
5. Connect the device via USB — accept the "Allow USB debugging?" prompt on the device

### Verify device is connected

```bash
adb devices
```

Expected output:
```
List of devices attached
XXXXXXXXXXXXXXXX  device
```

If the status is `unauthorized`, re-accept the USB debugging prompt on the device.

---

## Running the App

### First-time native build (mandatory)

The app uses Mapbox and expo-location which require native modules — Expo Go cannot run this app.

```bash
# From the monorepo root
pnpm --filter @fomo/mobile android
# or: cd apps/mobile && pnpm expo run:android
```

This compiles the Android APK and installs it on the connected device (~10–15 min first time).

### Metro + adb reverse (subsequent JS-only changes)

After the native build is installed, JS changes only need Metro — no recompile:

```bash
# Forward Metro port so the phone can reach your machine
adb reverse tcp:8081 tcp:8081

# Start Metro
pnpm --filter @fomo/mobile start
```

Open the FOMO app on the device — it connects to Metro over USB.

### When to rebuild native vs reload Metro

| Change type | Action needed |
|---|---|
| JS/TS only | Metro reload (shake device → Reload) or `r` in Metro terminal |
| New npm package with native module | `pnpm --filter @fomo/mobile android` (full native rebuild) |
| `app.json` / `app.config.js` | Full native rebuild |
| Android Gradle files | Full native rebuild |
| `.env` changes | Restart Metro with `pnpm --filter @fomo/mobile start:clear` |

---

## Package Management (ADB)

```bash
# List installed packages — find the FOMO package name
adb shell pm list packages | grep -i fomo
# Expected: package:com.fomo.mobile

# Clear all app data (tokens, permissions, cached state) — same as uninstall+reinstall
adb shell pm clear com.fomo.mobile

# Uninstall the app
adb uninstall com.fomo.mobile

# Install a pre-built APK
adb install -r apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk

# Launch the app
adb shell am start -n com.fomo.mobile/.MainActivity
```

---

## Logcat

### Stream all logs from the FOMO process

```bash
# Get the PID after launching the app
PID=$(adb shell pidof com.fomo.mobile)
adb logcat --pid=$PID
```

### Filter by tag

```bash
# React Native JS logs only
adb logcat ReactNativeJS:V *:S

# All React Native logs
adb logcat ReactNative:V *:S

# Crash / fatal errors
adb logcat AndroidRuntime:E *:S

# Everything + crash filter in PowerShell
adb logcat | Select-String "ReactNativeJS|FATAL|AndroidRuntime|Exception"
```

### Save logcat to file

```bash
adb logcat > debug.log
```

Press Ctrl+C to stop. Open `debug.log` in any editor.

---

## Auth / Keycloak Debugging

### Check the redirect URI

The auth provider logs the redirect URI at startup (dev builds only):

```
[auth] redirect URI: fomo://
```

Look for this in Metro console or in logcat (`ReactNativeJS` tag).
This URI must be registered in the Keycloak client's **Valid redirect URIs** as `fomo://*` or exactly `fomo://`.

### Common Keycloak errors

| Error | Cause | Fix |
|---|---|---|
| "Client not found" | Wrong realm in `.env` | Set `EXPO_PUBLIC_KEYCLOAK_REALM=fomo-users` (not `fomo-admin`) |
| "Redirect URI mismatch" | Keycloak client doesn't have `fomo://*` | Add `fomo://*` to Valid redirect URIs in Keycloak |
| Browser opens but no redirect back | `WebBrowser.maybeCompleteAuthSession()` not called | Ensure it's called at module level in `auth-provider.tsx` |
| 401 from `/api/v1/users/me` | Backend doesn't accept `fomo-users` issuer | Add `AUTH_OIDC_EXTRA_ISSUERS=https://auth.staging.fomo-lab.org/realms/fomo-users` to API env |
| Login loop | Auth state not persisting | Check SecureStore write in `storeTokens` |

### SecureStore / session cleanup

```bash
# Wipe all stored tokens by clearing app data
adb shell pm clear com.fomo.mobile
```

After clearing, the app should show the login gate on next launch.

### Manually test token expiry

1. Store a token, set your system clock forward past exp time
2. Restart the app — `isTokenExpired()` should detect expiry and clear the session

---

## Location Permission Debugging

### Reset permissions

```bash
# Reset all permissions to default
adb shell pm clear com.fomo.mobile
# OR reset only location:
adb shell pm revoke com.fomo.mobile android.permission.ACCESS_FINE_LOCATION
adb shell pm revoke com.fomo.mobile android.permission.ACCESS_COARSE_LOCATION
```

### Check current permission state

```bash
adb shell dumpsys package com.fomo.mobile | grep -i "LOCATION\|permission"
```

### "Never ask again" is cached

Android caches the permission denial. If "Never ask again" was selected:
- `requestForegroundPermissionsAsync()` returns `denied` without a dialog
- User must go to **Settings → Apps → FOMO → Permissions → Location → Allow**
- Clearing app data (`pm clear`) resets this cache

---

## Mapbox / Native Rebuild Notes

Mapbox Maps SDK downloads its native `.aar` using the Gradle secret token. If the download fails:

1. Verify `MAPBOX_DOWNLOADS_TOKEN=sk.…` is in `~/.gradle/gradle.properties`
2. Confirm the token starts with `sk.` not `pk.`
3. Check network access to `api.mapbox.com`

After adding/changing the token:
```bash
# From apps/mobile/android
.\gradlew.bat assembleDebug --no-build-cache
```

---

## Gradle Cache / Build Cleanup

### Normal clean

```bash
cd apps/mobile/android
.\gradlew.bat clean
```

### Full cache reset (fixes most "dirty build" issues)

```powershell
# Delete the Android app build directory
Remove-Item -Recurse -Force apps/mobile/android/app/build
Remove-Item -Recurse -Force apps/mobile/android/app/.cxx

# Clear Gradle's pre-dexed AAR transforms cache
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches\transforms-3"
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches\transforms-4"

# Rebuild without cache
cd apps/mobile/android
.\gradlew.bat assembleDebug --no-build-cache
```

### Windows-specific: CMake / Ninja errors on `clean`

The `clean` task runs `externalNativeBuildCleanDebug` which can fail on Windows with:
```
ninja: error: rebuilding 'build.ninja': subcommand failed
```

Fix: delete the `.cxx` directory manually (see above) instead of relying on `gradlew clean`.

---

## Common Errors

### Intent / UI changes not appearing on device after Metro reload

**Symptom**: `start:clear` + shake-reload still shows the old UI. Styles look like plain text or are completely absent.

**Root cause**: Two distinct scenarios both produce this symptom.

1. **The APK has a bundled JS snapshot.** Some build paths (e.g. `gradlew assembleRelease`, or an old dev build whose embedded bundle was never cleared) include a pre-packed bundle inside the APK. Metro never gets contacted; the app loads the stale bundle directly from disk.

2. **Metro's transform cache is stale even after `start:clear`.** This is rarer but happens when the cache directory itself is partially corrupt.

**Fix — definitive sequence (in this order):**
```powershell
# 1. Kill any running Metro

# Terminal 1 — start Metro with a fully cleared cache
cd apps/mobile
pnpm start:clear

# Terminal 2 — once Metro shows "waiting on exp://..."
adb reverse tcp:8081 tcp:8081

# Build a fresh debug APK (debug builds always load JS from Metro)
cd apps/mobile/android
.\gradlew assembleDebug

# Install, replacing whatever was there
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

A debug APK built this way always fetches JS from Metro at runtime — there is no embedded bundle. Changes are now guaranteed to be live.

**Diagnosis shortcut**: add a temporary `backgroundColor: 'red'` to any root container. If the screen is still not red after a Metro reload + shake, the device is not talking to Metro at all and the full rebuild above is needed.

**History**: this issue surfaced repeatedly during FOMO-171 intent button work. Commits `5969abb`, `f7b8870`, `487d561` were all created specifically to diagnose stale-cache symptoms by making styling "unmistakably different." The root cause was always a pre-built APK ignoring Metro.

---

### `Pressable` visual styles silently ignored on Android

**Symptom**: `borderWidth`, `borderColor`, `backgroundColor` set on a `Pressable` have no visible effect on Android. The component renders as unstyled text/icon with no button shape, even though the same code appears to work in the simulator or on iOS.

**Root cause**: On Android, the `Pressable` component's internal touch handling layer can intercept or override visual styles applied directly to the `Pressable` node — particularly border and background properties. This is a known React Native platform inconsistency.

**Fix**: Use a `Pressable > View` pattern. The `Pressable` is a bare touch target only; all visual styling lives on an inner `View`.

```tsx
// ❌ Unreliable on Android — border/background may be ignored
<Pressable style={[styles.btn, isActive && styles.btnActive]} onPress={...}>
  <Icon />
  <Text>Label</Text>
</Pressable>

// ✅ Reliable cross-platform
<Pressable onPress={...} style={styles.pressable}>   {/* touch target only */}
  {({ pressed }) => (
    <View style={[styles.btn, isActive && styles.btnActive, pressed && styles.btnPressed]}>
      <Icon />
      <Text>Label</Text>
    </View>
  )}
</Pressable>
```

Also set `android_ripple={null}` to suppress the platform ink ripple, which overflows `borderRadius` on older API levels when inside a `BlurView`.

**Affected component**: `components/fomo/IntentSelector.tsx` — fixed in FOMO-171 UI polish.

---

### React 19: "Cannot update a component while rendering a different component"

**Symptom**: A full-screen red error overlay appears immediately on launch or when tapping a filter chip. The stack trace shows `setState` being called inside `basicStateReducer` during another component's render.

**Root cause**: React 19 (used via RN 0.81) treats calling a parent's `setState` inside a `useState` functional updater as a hard error. Functional updaters (`setState(prev => ...)`) are called during the render phase, so any parent state dispatch inside them violates the rule.

**Specific instance (FOMO, 2026-06)**: `SearchBar.handleToggleCategory` called `onFilterChange(next)` (which calls `setActiveCategories` in `DiscoveryScreen`) inside the `setSelectedFilters` functional updater.

```tsx
// ❌ Triggers the React 19 error — onFilterChange runs during render
setSelectedFilters((prev) => {
  const next = [...prev, id];
  onFilterChange?.(next);   // parent setState called inside updater = ERROR
  return next;
});

// ✅ Compute next value first, then call both setters in the event handler
const next = selectedFilters.includes(id)
  ? selectedFilters.filter((f) => f !== id)
  : [...selectedFilters, id];
setSelectedFilters(next);
onFilterChange?.(next);
```

**File fixed**: `components/fomo/search-bar.tsx` — `handleToggleCategory`.

---

### `NoClassDefFoundError: expo.modules.kotlin.types.AnyTypeCache`

**Cause**: Expo packages installed at a version incompatible with the installed `expo` SDK.
For example, `expo-auth-session@^56.x` with `expo@~54.0.0`.

**Fix**: Pin all Expo packages to SDK-compatible versions. Check `bundledNativeModules.json`:

```bash
cat node_modules/expo/bundledNativeModules.json | grep "auth-session\|secure-store\|web-browser"
```

Use those exact `~x.y.z` version ranges in `apps/mobile/package.json`, then:

```bash
pnpm install --filter @fomo/mobile
# Then full clean rebuild:
Remove-Item -Recurse -Force apps/mobile/android/app/build
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches\transforms-3"
cd apps/mobile/android && .\gradlew.bat assembleDebug --no-build-cache
```

### App stuck on loading spinner

- Metro not connected → run `adb reverse tcp:8081 tcp:8081`
- JS bundle failed to load → check Metro console for syntax errors
- Auth session restore hanging → check logcat for `[auth]` tag errors

### Metro not connecting to phone

```bash
adb reverse tcp:8081 tcp:8081
# Then restart Metro
pnpm --filter @fomo/mobile start:clear
```

If `adb devices` shows the device as `offline`, unplug and replug USB, then re-accept the debugging prompt.

### "Client not found" in Keycloak

The mobile app is connecting to the wrong realm. Ensure:
```
EXPO_PUBLIC_KEYCLOAK_REALM=fomo-users   # not fomo-admin
```
in `apps/mobile/.env`, then restart Metro with `start:clear`.

### Redirect URI mismatch after login

1. Check logged redirect URI: `[auth] redirect URI: fomo://`
2. Open Keycloak admin → Realm: `fomo-users` → Client: `fomo-mobile` → Valid redirect URIs
3. Add `fomo://*` if missing

### Location permission dialog never appears

- Permission was previously denied with "Never ask again"
- Run `adb shell pm clear com.fomo.mobile` to reset, or grant manually in Android Settings

---

## Safe Rules

1. **Never log tokens** — not in Logcat, not in Metro console, not in Sentry
2. **Never commit `.env`** — it contains real Mapbox and API credentials
3. **Use SDK-compatible Expo package versions** — always check `bundledNativeModules.json`
4. **Always `adb reverse tcp:8081 tcp:8081`** before starting Metro with a USB-connected device
5. **Use `pm clear` to reset state** rather than manual SecureStore manipulation

---

## Quick Reference

```bash
# Check connected devices
adb devices

# Clear app data (tokens + permissions)
adb shell pm clear com.fomo.mobile

# Stream JS logs
adb logcat ReactNativeJS:V *:S

# Stream crash logs
adb logcat AndroidRuntime:E *:S

# Forward Metro port
adb reverse tcp:8081 tcp:8081

# Start Metro
pnpm --filter @fomo/mobile start

# Full native rebuild
pnpm --filter @fomo/mobile android

# Build APK only (no Metro)
cd apps/mobile/android && .\gradlew.bat assembleDebug

# Install pre-built APK
adb install -r apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk
```
