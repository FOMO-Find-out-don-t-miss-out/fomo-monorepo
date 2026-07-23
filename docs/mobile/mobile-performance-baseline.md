# Mobile Performance Baseline & Responsiveness RCA (FOMO-174)

Status: **instrumentation complete; physical-device smoke run captured; full
repeated baseline and release comparison pending**.
App commit at time of audit: `74e40e3` (plus the FOMO-174 instrumentation changes).

This document separates these classes of statements throughout:

- **[MEASURED — SMOKE]** — captured on the physical device during the initial
  smoke run (§1a). Sample size 1–2 per flow, debug build, Metro attached — a
  sanity pass, **not** suitable for median/min/max conclusions.
- **[MEASURED]** — backed by the repeated (5-run) protocol of §12. None exist
  yet; the §4 results table is still `Pending physical-device run`.
- **[STATIC]** — directly observable in the committed source code (file/line
  cited). These are facts about what the code does, not about how slow it is.
- **[HYPOTHESIS]** — a plausible performance consequence of a static finding
  that still requires measurement before it may be called a bottleneck.

---

## 1. Executive summary

The app is small (4 tab screens, ~20 components) and its data layer is plain
`fetch` + `useState` hooks with no cache. The static audit found no single
"smoking gun", but a cluster of patterns that plausibly compound into the
perceived sluggishness, in rough order of expected impact:

1. **Every Discover focus refetches intent state for _all_ loaded events** —
   one `event_ids` query parameter per event, unbounded ([STATIC], see §5).
2. **The Discover carousel is a non-virtualized `ScrollView`** that mounts every
   event card and starts every card image download immediately ([STATIC], §6).
3. **Unmemoized cards with inline callbacks**: any Discover state change
   (each search keystroke, card selection, intent toggle) re-renders every
   card and the Mapbox view ([STATIC], §6).
4. **Auth boot is a fully sequential chain** (SecureStore read → Keycloak
   refresh exchange → SecureStore writes → `GET /users/me`) that blocks the
   first usable screen behind two network round-trips ([STATIC], §5).
5. **Intent actions are server-authoritative, not optimistic**: the final
   button state (and on My Events, the sheet close) waits for the network,
   and each action triggers 1–2 follow-up refetches ([STATIC], §5).
6. **My Events replaces its list with a full-screen spinner on every focus**
   because refetch sets `isLoading` and the previous list is not kept ([STATIC], §6).
7. **Debug-build overhead** (Metro, dev-mode JS, Mapbox/Reanimated/BlurView in
   dev) inflates everything; a local release build exists to quantify this (§8).

A first smoke run (§1a) has since confirmed the *mechanisms* behind items 1, 2,
3 and 5 with preliminary numbers, and surfaced one new finding (duplicate My
Events requests on first focus). Final ranking still waits for the repeated
§12 protocol and the release comparison.

---

## 1a. Preliminary physical-device smoke results [MEASURED — SMOKE]

Conditions: physical Android device, **debug build, Metro attached**, staging
API, `EXPO_PUBLIC_PERF_DEBUG=true`, render counters enabled (see the observer
caveat below). Sample size: **1–2 captures per flow** — treat every number as
preliminary; none of this feeds the §4 median/min/max table.

**Authenticated startup** (2 runs)
- JS init → `auth-gate-resolved`: 1649 ms / 2652 ms.
- `auth-bootstrap-resolved duration_ms`: 1157 ms / 902 ms — of which
  refresh exchange 440 ms / 307 ms and `GET /users/me` 463 ms / 424 ms,
  confirming the sequential chain adds two full network round-trips before
  the first screen.
- `fonts-ready`: 329 ms vs 1492 ms — high variance between runs; cause not yet
  isolated (dev-mode asset loading is a suspect, not a finding).

**Discover**
- Discovery returned **70 events**; `discover-render cards_rendered=70` — the
  carousel mounts **all** returned events. Promoted from hypothesis.
- Discover focus → `discover-render`: ~1817 ms / ~1705 ms.
- Startup showed **duplicate discovery + intents request cycles**, matching the
  location-resolution double-fetch identified statically. Promoted.
- Intent batch requests: `id_batch=70`, `query_len=3290`; durations
  **496–1247 ms**. Promoted — the full-batch refetch is real and slow enough
  to matter.
- `EventCard` render counter reached ~350 during initial load ≈ **five full
  70-card render passes**. Promoted — repeated full-carousel renders happen.

**Intent action (one interaction)**
- Mutation round trip: 624 ms; a full 70-ID intents refetch followed it —
  server-authoritative latency confirmed as measured behavior.
- The single interaction added another ~350 EventCard renders (~5 more full
  carousel passes) and re-rendered `DiscoverScreen`, `FomoMap`, `EventDetails`
  and `IntentSelector`.

**Event Details**
- open-start → modal-shown: 182 ms; → animation-done: 303 ms. **Not currently
  indicated as a primary bottleneck.**

**Navigation**
- Discover tab-tap → My Events focus ≈ 73 ms; My Events → Discover ≈ 43 ms.
  **Navigation itself is not currently indicated as a bottleneck.**

**My Events**
- **Four** `GET /api/v1/me/events` calls on first focus — two per relationship
  type instead of the expected total of two. Preliminary attribution: the
  mount-time hook effect plus the focus-triggered refetch both firing
  (`use-my-events.ts` effect on `accessToken` + `useFocusEffect` tick bump)
  — kept **preliminary until cycle-correlated logs confirm the source**.
- Focus → stable rendered list ≈ 435 ms.

**Map**
- `style-loaded` ≈ 743 ms after mount; **no** second `style-loaded` after
  leaving and returning to Discover — map remounting is not indicated.

**Observer-effect caveat**: this smoke run had per-component render logging
enabled, which itself emits hundreds of console lines during Discover load and
inflates JS-thread timings by an unquantified amount. Render counting has since
been moved behind its own flag (`EXPO_PUBLIC_PERF_RENDER_DEBUG`, §14) so the
repeated timing runs are not distorted; the ~350-render counts remain valid as
render-behavior evidence, but the timing numbers above should be re-captured
without render logging.

---

## 2. Test environment

To be filled in by the person running the protocol. Record for **every** run:

| Field | Value |
| ----- | ----- |
| Device model | _pending_ |
| Android version | _pending_ |
| Build type | debug (Metro attached) / release |
| Metro attached | yes/no |
| JS debugger / DevTools open | yes/no |
| Network | Wi-Fi / LTE (same for all runs) |
| API environment | staging |
| App commit | `git rev-parse --short HEAD` |
| `EXPO_PUBLIC_PERF_DEBUG` | true/false |
| `EXPO_PUBLIC_PERF_RENDER_DEBUG` | true/false (**must be false for timing runs**) |

---

## 3. Measurement definitions

All instrumentation is gated behind `EXPO_PUBLIC_PERF_DEBUG=true` **and**
`__DEV__` (see §14). Log lines are single-line `[perf]` key=value records.

| Metric | Starts | Ends | Source |
| ------ | ------ | ---- | ------ |
| `milestone name=root-layout-mounted t_since_js_init_ms` | JS evaluation of `utils/performance-debug.ts` (NOT native process launch — JS cannot see native init; in dev this also excludes bundle download only partially) | `RootLayout` first mount effect | `app/_layout.tsx` |
| `milestone name=fonts-ready` | same origin | Inter fonts resolved, splash hidden | `app/_layout.tsx` |
| `milestone name=auth-bootstrap-resolved path=… duration_ms` | start of the session-restore effect | `isLoading` set false; `path` is one of `refresh-exchange`, `stored-access`, `refresh-failed`, `no-session` | `providers/auth-provider.tsx` |
| `milestone name=auth-gate-resolved authenticated=…` | same origin as milestones | first render where AuthGate stops blocking → first usable screen | `app/_layout.tsx` |
| `request method=… endpoint=… duration_ms=… status=… id_batch=… query_len=… bytes=…` | fetch dispatched | response headers+body received. `endpoint` is query-stripped and UUID-normalized; `id_batch` counts `event_ids=` params; `bytes` is the `content-length` header when the server sends one (estimate; absent on chunked responses) | `utils/api-client.ts`, `/users/me` in `providers/auth-provider.tsx` |
| `screen-focus` / `screen-blur` `screen=… cycle=… t=…` | — | fired by `useFocusEffect`; `t` is a raw monotonic ms timestamp on the same clock as `nav-tap t` | `usePerfScreenFocus` |
| `nav-tap to=… t=…` | user presses a tab button | — (subtract from destination `screen-focus t` for tap→focus latency) | `app/(tabs)/_layout.tsx` |
| `discover-events count=…` | — | discovery response parsed; `count` = events returned by the API | `hooks/use-discovery.ts` |
| `discover-render events_total=… cards_rendered=…` | — | first commit after loading settles; `cards_rendered` = cards mounted by the carousel (it mounts **all** filtered events — no virtualization) | `app/(tabs)/index.tsx` |
| `intents-fetch phase=start count=…` | intent batch request about to start; `count` = number of event IDs in the batch (IDs themselves are never logged) | — (duration comes from the matching `request endpoint=/api/v1/me/event-relationships` line) | `hooks/use-event-relationships.ts` |
| `intent-toggle screen=… phase=tap/mutation-done/settled duration_ms` | user presses Interested/Going | `tap`→`mutation-done` = API round trip; `settled` = pending spinner cleared. Immediate visual feedback (spinner) appears in the commit right after `tap` | Discover + My Events screens |
| `sheet phase=open-start/modal-shown/open-anim-done cycle=… duration_ms` | parent set the `event` prop (the commit immediately after card/pin press) | `modal-shown` = RN `Modal.onShow` (native modal visible); `open-anim-done` = 300 ms slide-in finished. Compare cycle 1 vs later cycles for first-open vs subsequent-open | `components/fomo/event-details.tsx` |
| `my-events-fetch type=… count=…` | — | list response parsed | `hooks/use-my-events.ts` |
| `my-events-render tab=… rows=…` | — | commit after loading settles | `app/(tabs)/saved.tsx` |
| `map phase=style-loaded/fully-rendered since_mount_ms=… markers=…` | first `FomoMap` render | Mapbox `onDidFinishLoadingMap` / `onDidFinishRenderingMapFully` | `components/fomo/fomo-map.tsx` |
| `render component=… count=…` | — | cumulative render count per component. `EventCard` sampled every 25 renders, `MyEventListItem` every 10; all others logged every render. **Gated by `EXPO_PUBLIC_PERF_RENDER_DEBUG`, not the main timing flag** — high-volume render logging distorts timing measurements (observer effect), so it stays off during benchmark runs | `perfCountRender` |
| `image sample=… duration_ms` | `ImageBackground.onLoadStart` | `onLoadEnd`; capped at 6 sampled card images per session so the measurement doesn't perturb the run | `components/fomo/event-card.tsx` |

Honest limitations:

- **Cold-start native time is not measurable from JS.** `t_since_js_init_ms`
  starts when the JS bundle begins executing. For true cold start use a
  stopwatch/screen recording (tap icon → first frame) alongside the JS
  milestones, or `adb shell am start -W` for TTID.
- **Release builds strip all of this** (`__DEV__` is false by design — the flag
  must not ship). Debug-vs-release comparison therefore uses screen recording /
  stopwatch for the same flows, not `[perf]` logs.
- A render count alone is not evidence of a problem; it must be correlated with
  interaction latency or frame drops.

---

## 4. Results table

All values `Pending physical-device run`. Fill from the protocol in §12.

| Flow | Build | Runs | Median | Min | Max | API calls | Notes |
| ---- | ----- | ---: | -----: | --: | --: | --------: | ----- |
| Cold app start (icon → first frame, stopwatch) | debug | – | Pending physical-device run | – | – | – | |
| Cold app start (JS init → auth-gate-resolved) | debug | – | Pending physical-device run | – | – | – | |
| Warm app start | debug | – | Pending physical-device run | – | – | – | |
| Authenticated boot (`auth-bootstrap-resolved`) | debug | – | Pending physical-device run | – | – | expected 2 (Keycloak + `/users/me`) | |
| Discover initial load (focus → cards rendered) | debug | – | Pending physical-device run | – | – | expected 2–4 (see §5) | |
| Discover refocus (tab return) | debug | – | Pending physical-device run | – | – | expected 1 (intents batch) | |
| Open Event Details (tap → modal-shown) | debug | – | Pending physical-device run | – | – | 0 | |
| Open Event Details (tap → open-anim-done) | debug | – | Pending physical-device run | – | – | 0 | |
| Interested/Going tap → mutation-done | debug | – | Pending physical-device run | – | – | 1 + 1–2 refetches | |
| My Events focus → stable list | debug | – | Pending physical-device run | – | – | 2 | |
| My Events tab switch (Interested ⇄ Going) | debug | – | Pending physical-device run | – | – | 0 | |
| Map style-loaded / fully-rendered | debug | – | Pending physical-device run | – | – | 0 | |
| Return from Map (= return to Discover) | debug | – | Pending physical-device run | – | – | 1 | map is Discover's layer 0, see §7 |
| Each of the above | release | – | Pending physical-device run | – | – | – | stopwatch/recording only |

---

## 5. API / request analysis

### Requests per flow — derived from code [STATIC]

| Flow | Requests | Sequential or parallel |
| ---- | -------- | ---------------------- |
| Auth boot (has refresh token) | SecureStore read → Keycloak token exchange → 2 SecureStore writes → `GET /users/me` | **fully sequential**; first screen blocked on the whole chain (`providers/auth-provider.tsx:127-165`, AuthGate in `app/_layout.tsx`) |
| Discover cold load | `GET /events/discovery` ×1–2, `GET /me/event-relationships` ×1–2 | discovery→intents sequential (intents need the ID list). The ×2 arises when device location resolves after the first fetch: `use-discovery`'s effect depends on `lat/lng`, so default-location results are fetched and then thrown away when real coords arrive (`hooks/use-discovery.ts:53`, `hooks/use-device-location.ts`) |
| Discover refocus | `GET /me/event-relationships` (full batch) | one request; fired unconditionally by `useFocusEffect` (`app/(tabs)/index.tsx:115-119`) |
| Intent toggle (Discover) | `PUT`/`DELETE` relationship → full intents batch refetch | sequential |
| Intent toggle (My Events) | `PUT`/`DELETE` → `GET /me/events?relationship_type=interested` + `GET …=going` | mutation sequential, the two refetches run **concurrently** |
| My Events focus | both list GETs | concurrent (two independent hook effects, `app/(tabs)/saved.tsx:135-137`) |
| Map / Profile / Search focus | none | — |

### Largest ID batches / query strings [STATIC]

`fetchEventIntents` builds one `event_ids=<uuid>` pair per loaded event
(`utils/event-relationships-api.ts:29`), re-sent on **every** Discover focus
and after every intent toggle. [MEASURED — SMOKE]: with 70 events the request
carried `id_batch=70`, `query_len=3290`, and took **496–1247 ms** against
staging — promoted from hypothesis to preliminary measured finding.

- The batch always covers **all events returned by the discovery API** — not
  just visible cards (`eventIds` is built from the full `eventsWithDistance`
  array, `app/(tabs)/index.tsx:95`).

### Duplicates / races [STATIC]

- Startup double discovery fetch described above. [MEASURED — SMOKE]: the
  smoke run observed duplicate discovery **and** intents request cycles at
  startup — promoted from hypothesis. Both `use-discovery` and
  `use-event-relationships` have correct `cancelled` cleanup, so late
  responses don't overwrite newer state, but the wasted requests still cost
  time and (dev) JS work.
- [MEASURED — SMOKE, attribution preliminary]: **four** `GET /api/v1/me/events`
  calls on first My Events focus — two per relationship type, double the
  expected count. Consistent with the mount-time effect and the
  focus-refetch tick both firing, but the exact source awaits
  cycle-correlated confirmation in the repeated run.
- `useEffect(() => setLocalIntents({}), [serverIntents])`
  (`app/(tabs)/index.tsx:108-110`) fires an extra state update after **every**
  intents response, even a no-op one, because `serverIntents` is always a new
  object → one extra full-screen render per intents fetch.
- No request cancellation/abort exists (no `AbortController`); slow requests
  run to completion.

### Longest requests

`Pending physical-device run` — read from `request … duration_ms` logs.

---

## 6. Rendering analysis

All items below are **[STATIC]** code observations with **[HYPOTHESIS]**-level
performance impact until correlated with measurements.

**Discover screen (`app/(tabs)/index.tsx`)**
- The carousel is a plain horizontal `ScrollView` mapping over
  `filteredEvents` — **no virtualization**: every event becomes a mounted
  `EventCard`, and every card image starts downloading immediately
  (`index.tsx:274-293`). [MEASURED — SMOKE]: `cards_rendered=70` of 70 events
  returned — all cards mount. Promoted from hypothesis.
- [MEASURED — SMOKE]: the `EventCard` render counter reached ~350 during one
  initial Discover load (≈ five full 70-card render passes), and a single
  intent interaction added another ~350 while also re-rendering
  `DiscoverScreen`, `FomoMap`, `EventDetails` and `IntentSelector` — the
  whole-tree re-render fan-out is real, not just theoretical. (Counts were
  captured with render logging on, which adds its own overhead; the counts
  are valid, the co-captured timings are inflated — see §1a caveat.)
- `EventCard` is **not memoized** and receives a new inline
  `onPress={() => setSelectedEvent(event)}` closure each render. Consequently
  every Discover state change re-renders all cards. State changes include:
  every search keystroke (`searchText` lives on the screen), card selection,
  `pendingEventId` set/clear, the `localIntents` clear effect, and the
  `locateMe` 600 ms reset timer.
- `eventsWithDistance` produces new object identities whenever `events` or
  location change, invalidating downstream memos in one shot.
- The `render component=DiscoverScreen/EventCard/FomoMap count=…` logs will
  quantify all of this per interaction.

**Carousel swiping** — cards animate scale via `Animated.spring` on the native
driver (fine). Because all cards are mounted, swiping itself does no mounting
work; the cost is concentrated at load time. JS-thread stalls while swiping:
`Pending physical-device run` (observe via React DevTools profiler / frame
drops).

**Event Details sheet (`components/fomo/event-details.tsx`)**
- RN `Modal` + `Animated.timing` (native driver) with a 300 ms slide. Content
  fully remounts on every open (the `Modal` unmounts children when `visible`
  is false) — remount cost is small (text + icons, no data fetch) but shows up
  in `EventDetails` render counts and `sheet` timings.
- Intent state is passed in from the parent; **sheet presentation is not
  blocked by any fetch** [STATIC].
- `BlurView intensity={20}` backs the sheet (and the tab bar); Android blur is
  comparatively expensive — impact `Pending physical-device run`.

**IntentSelector** — trivial component; re-renders whenever its parent sheet
re-renders. Render feedback for a tap requires the full Discover/My Events
screen re-render to propagate `isPendingIntent` down — the render counters will
show the fan-out.

**My Events (`app/(tabs)/saved.tsx`)**
- Non-virtualized `ScrollView` of rows — acceptable at current list sizes,
  linear growth risk later.
- On every focus `refetchBoth()` sets `isLoading` on the active hook, and the
  screen renders `FomoLoadingState` **instead of the previous list**
  (`saved.tsx:283-291`) — a full-content flash on every tab visit even when
  nothing changed. This is a perceived-responsiveness defect visible in code.
- Rows are unmemoized with inline `onPress` closures; date grouping
  (`groupAndSort`) is memoized correctly.
- After a toggle the sheet closes only **after** the mutation round trip
  (`saved.tsx:157-183`), then both lists refetch → user-visible latency chain.

**Map (`components/fomo/fomo-map.tsx`)**
- The map is **layer 0 of Discover** — there is no separate Map tab/screen.
  "Discover → Map" transitions in the task spec translate to "Discover focus"
  here.
- The Mapbox view stays mounted while the Discover tab remains in the tab
  stack (expo-router keeps visited tab screens mounted), so returning to
  Discover should not re-init the map — confirm via `map phase=style-loaded`
  appearing only once per session (`Pending physical-device run`).
- `FomoMap` re-renders on every Discover render; pin GeoJSON is memoized
  (good), but `handlePinPress` is recreated each render and passed to the
  native `ShapeSource`, and Camera props are recomputed each time. Whether
  this causes native churn: [HYPOTHESIS].
- Markers are simple circle layers fed by one `ShapeSource` — an efficient
  pattern; marker count is logged.

---

## 7. Image analysis [STATIC]

- Component: plain React Native `ImageBackground` (`event-card.tsx`) — the
  only image usage in the app. `expo-image` is **not** installed.
- Caching: whatever the platform HTTP stack provides; no explicit cache policy,
  no placeholders, no priority hints, no `recyclingKey`.
- Sizing: the card is fixed 260×180, but the **source** image is whatever URL
  the backend supplies (`photoUrl`) — no server-side resize parameters are
  requested, so oversized downloads are plausible [HYPOTHESIS; check the
  `image sample=… duration_ms` logs plus the URL dimensions].
- Because the carousel mounts all cards, **all card images begin loading on
  initial Discover render** — count = `cards_rendered` in the
  `discover-render` log.
- Sampled load timings (6 per session): `Pending physical-device run`.

---

## 8. Debug versus release/profile comparison

Inspected `apps/mobile/android/app/build.gradle`: the `release` build type is
**signed with the debug keystore** (line 137), so a local release install is
possible without any signing setup. Valid commands for this repository:

```bash
# Debug + Metro (the everyday dev loop)
pnpm --filter @fomo/mobile start          # Metro
adb reverse tcp:8081 tcp:8081             # mandatory for physical devices
pnpm --filter @fomo/mobile android        # expo run:android (debug)

# Release variant (bundled JS, no Metro, __DEV__ = false)
pnpm --filter @fomo/mobile exec expo run:android --variant release
```

Notes:
- The release variant does **not** emit `[perf]` logs (`__DEV__` gate). Compare
  flows with screen recording (slow-motion camera or `adb shell screenrecord`)
  and stopwatch timing of the same protocol.
- `minifyEnabled` follows `android.enableMinifyInReleaseBuilds` from
  `gradle.properties`; no Hermes/profile-specific variant exists. A dedicated
  `profileable` build is **not currently configured** — the smallest safe
  addition would be a `profile` build type inheriting from release with
  `profileable true`, but that is follow-up work, not part of this task.
- Expect Mapbox, Reanimated worklets and BlurView to be substantially faster
  outside dev mode; how much is `Pending physical-device run`.

---

## 9. Root cause analysis

No bottleneck can honestly be labeled "confirmed" without the device runs.
The table records the RCA skeleton with current confidence based on static
evidence alone; confidence values below mean "confidence that this materially
affects perceived responsiveness", not "confidence the code does this" (the
code citations are certain).

| # | Symptom | Root cause (mechanism) | Evidence | Confidence | Affected flows | Recommended fix (follow-up) |
| - | ------- | ---------------------- | -------- | ---------- | -------------- | --------------------------- |
| 1 | Delay/network chatter on every Discover focus | Unconditional full-batch intents refetch for all loaded events | [STATIC] `index.tsx:115-119` + [MEASURED — SMOKE] id_batch=70, query_len=3290, 496–1247 ms | medium-high (preliminary) | Discover refocus, intent toggle | T1 |
| 2 | Slow first Discover paint, heavy image traffic | Non-virtualized carousel mounts all cards + starts all image loads | [STATIC] `index.tsx:274-293` + [MEASURED — SMOKE] cards_rendered=70; focus→render ~1.7–1.8 s (render-logging inflated) | medium-high (preliminary) | Discover initial load | T3, T4 |
| 3 | Sluggish typing/interactions on Discover | Screen-level state + unmemoized cards → whole-tree re-renders incl. Mapbox | [STATIC] §6 + [MEASURED — SMOKE] ~350 EventCard renders per load and per intent interaction | medium-high (preliminary) | Discover interactions | T2 |
| 4 | Long wait on app open | Sequential auth chain blocks first screen behind 2 network round-trips | [STATIC] `auth-provider.tsx:127-165` + [MEASURED — SMOKE] bootstrap 902–1157 ms (exchange 307–440 + /users/me 424–463) | medium-high (preliminary) | Cold/warm start | T5 |
| 5 | Intent buttons feel slow to "commit"; My Events sheet hangs before closing | Server-authoritative toggles: state settles only after mutation (+refetches) | [STATIC] `index.tsx:121-150`, `saved.tsx:157-183` + [MEASURED — SMOKE] mutation 624 ms + full 70-ID refetch after | medium-high (preliminary) | Interested/Going | T6 |
| 6 | Content flash/spinner on every My Events visit | Refetch-on-focus discards the rendered list while loading | [STATIC] `saved.tsx:283-291` | **high** (mechanism directly visible; no timing needed for the flash itself) | My Events focus | T7 |
| 7 | Everything feels slower than it will in production | Dev-mode JS + Metro + dev Mapbox/Reanimated/Blur | [STATIC] build config; magnitude pending release run | high that it exists, magnitude pending | all | T8 |
| 8 | Wasted startup work | Duplicate discovery+intents fetch when device location resolves | [STATIC] `use-discovery.ts:53` + [MEASURED — SMOKE] duplicate cycles observed at startup | medium-high (preliminary) | Cold start → Discover | T1/T5 |
| 9 | Doubled My Events network cost on first focus | Mount-effect fetch + focus refetch both fire (attribution preliminary) | [MEASURED — SMOKE] 4× `GET /me/events` on first focus | medium (source unconfirmed) | My Events first focus | T7 |

"(preliminary)" = supported by the 1–2-sample smoke run; final ranking and
magnitudes wait for the repeated §12 protocol and the release comparison.

---

## 10. Top bottlenecks (expected user impact; ranking remains provisional until the repeated benchmark completes)

The smoke run supports the items below with preliminary numbers and has
additionally **cleared two suspects**: Event Details opening (182/303 ms) and
tab navigation itself (43–73 ms) are not currently indicated as primary
bottlenecks.

1. **Intent-state refetch storm on Discover focus/toggle** (RCA #1, #5) — it
   sits on the hot path of the two most frequent user actions.
2. **My Events focus flash** (RCA #6) — guaranteed visible regression on every
   tab visit; cheapest to verify.
3. **Non-virtualized, unmemoized Discover carousel + eager images** (RCA #2, #3).
4. **Sequential auth boot** (RCA #4) — bounded by two network RTTs to staging.
5. **Dev-build overhead** (RCA #7) — not user-facing in production but likely a
   large share of what is being felt today; quantify first so the other items
   are judged against release-build reality.

---

## 11. Quick wins (small, low-risk; NOT implemented in this task)

| Quick win | Expected impact | Effort | Risk | Evidence |
| --------- | --------------- | ------ | ---- | -------- |
| Keep previous My Events list visible during refetch (don't flip to spinner when data exists) | removes a guaranteed flash per focus | S | low | RCA #6 |
| `React.memo` on `EventCard` / `MyEventListItem` + stable `onPress` (e.g. pass `id`) | cuts N-card re-render per keystroke/selection | S | low | §6 |
| Skip `setLocalIntents({})` when already empty (or compare keys) | one fewer full-screen render per intents response | S | low | §5 |
| Debounce `onSearchChange` or keep text state inside `SearchBar` | avoids whole-screen (incl. map) render per keystroke | S | low | §6 |
| Skip intents refetch on focus when the ID set is unchanged **and** last fetch is fresh (<X s) | removes the most frequent redundant request | S–M | low-med (staleness window) | §5 |
| Don't fetch discovery until location status resolves (or short grace window) | removes duplicate cold-start fetch pair | S | low-med (delays first paint if location is slow — needs the measurement first) | §5 |

---

## 12. Benchmark protocol (manual, physical device)

Preparation:

1. `apps/mobile/.env`: add `EXPO_PUBLIC_PERF_DEBUG=true`. Leave
   `EXPO_PUBLIC_PERF_RENDER_DEBUG` **unset/false** for all timing runs — render
   logging is its own observer overhead and distorts the timings. Run the
   render-count observations (steps 5 and 7 render notes) as a **separate
   pass** with `EXPO_PUBLIC_PERF_RENDER_DEBUG=true`, and do not use timings
   from that pass.
2. `pnpm --filter @fomo/mobile start:clear` (env vars are inlined at bundle
   time — a plain reload is not enough), `adb reverse tcp:8081 tcp:8081`,
   `pnpm --filter @fomo/mobile android`.
3. Capture logs: Metro console shows them directly, or
   `adb logcat -s ReactNativeJS:V` and filter for `[perf]`
   (PowerShell: `adb logcat -s ReactNativeJS:V | Select-String "perf"`).
4. Same device, same network, screen recording running for anything needing
   visual timing. Log the §2 environment table once per session.
5. **5 runs per flow**; discard only clearly broken runs (crash, network
   outage) and say so; report **median / min / max**. Do not compute p95 from
   5 samples.

Flows (in order):

1. **Cold start**: force-stop app (`adb shell am force-stop com.<pkg>`), clear
   from recents, launch. Record stopwatch icon→first-frame AND the
   `milestone` lines (`root-layout-mounted`, `fonts-ready`,
   `auth-bootstrap-resolved`, `auth-gate-resolved`).
2. **Warm start**: background with Home, relaunch from icon. Same records.
3. **Authenticated boot**: from the cold-start logs — `auth-bootstrap-resolved
   duration_ms`, the Keycloak/`/users/me` `request` lines, and check for
   duplicate bootstrap calls (there should be exactly one).
4. **Discover initial load**: `screen-focus screen=discover` → `request
   /api/v1/events/discovery` → `discover-events count` → `discover-render
   cards_rendered` → `intents-fetch count` + its `request` line. Count total
   requests in the burst; note whether the discovery request fires twice
   (location resolution).
5. **Discover refocus**: go to Profile, return. Expect exactly one
   `intents-fetch` burst; record `id_batch`, `query_len`, `duration_ms`, and
   `render component=EventCard` growth.
6. **Event Details**: tap a card → `sheet open-start / modal-shown /
   open-anim-done`. Do 5 first-opens (different events) and 5 re-opens of the
   same event; compare cycle 1 vs later cycles.
7. **Interested/Going**: with the sheet open, tap Interested. Verify the
   spinner appears immediately (screen recording), record `intent-toggle`
   phases + the mutation `request` + the follow-up `intents-fetch`. Repeat
   for Going and for toggle-off. Note `render` counter growth on
   `DiscoverScreen`/`EventCard` to see whether the whole screen re-renders.
8. **My Events focus**: switch to My Events. Record both `my-events-fetch`
   lines (confirm they overlap in time = concurrent), `my-events-render rows`,
   focus→stable-list time, and whether the previous list flashes to a spinner.
9. **My Events tab switch**: Interested ⇄ Going 5×. Expect **zero** requests;
   record any render/jank observations.
10. **Map**: from the Discover cold load — `map style-loaded` /
    `fully-rendered` `since_mount_ms` + `markers`. On each return to Discover
    confirm no new `style-loaded` line (map not remounting).
11. **Navigation matrix**: Discover→My Events, My Events→Discover,
    Discover→Profile (and back). For each: `nav-tap t` → destination
    `screen-focus t` (Δ = tap→focus), then focus→usable content from the
    screen's own logs; note requests triggered.
12. **Release comparison**: build the release variant (§8) and repeat flows
    1, 2, 4, 6, 7 with stopwatch/screen-recording timing only.

---

## 13. Follow-up tickets (proposed)

Only tickets supported by §5–§9 findings; each should start by confirming the
relevant pending measurement.

- **T1 — Optimize Discover intent fetching**: refetch on focus only when the
  ID set changed or data is stale; consider limiting the batch or moving IDs
  to a POST body if `query_len` measurements are large; fold in the
  location-resolution double-fetch fix.
- **T2 — Cut Discover re-render fan-out**: memoize `EventCard`, stabilize
  callbacks, localize search-text state, guard the `localIntents` clear.
- **T3 — Virtualize/window the Discover carousel** (horizontal `FlatList`
  with tuned `initialNumToRender`/`windowSize`) — keep the same visuals.
- **T4 — Image loading strategy**: adopt `expo-image` (or equivalent) with
  caching, placeholders and explicitly sized/resized sources; depends on
  backend supporting resize params or measured evidence that sources are
  oversized.
- **T5 — Parallelize auth boot**: fire `/users/me` without blocking
  `isLoading`; first screen unblocks after the token exchange alone.
- **T6 — Optimistic intent updates**: apply state on tap, reconcile on
  response; on My Events close the sheet immediately.
- **T7 — My Events refresh strategy**: keep-previous-data on refocus; only
  show the spinner on true first load.
- **T8 — Profile/release workflow**: add a `profileable` build type and a
  short doc; optionally a permanently-compiled, sampling-based `[perf]`
  telemetry subset behind a runtime flag.

## 13a. Recommended execution order

1. **Run the §12 protocol** (debug + release) — everything else is prioritized
   by its numbers; the release run may deflate several hypotheses for free.
2. **T7** (My Events flash) — smallest certain win.
3. **T1** (intent refetch policy) — hottest path.
4. **T2 → T3 → T4** (Discover rendering/images) in that order: memoization is
   cheap and de-risks the FlatList migration; images last because they depend
   on backend capabilities.
5. **T5** (auth boot) — bounded, isolated change.
6. **T6** (optimistic intents) — product-behavior change, needs sign-off.
7. **T8** — alongside any of the above.

---

## 14. Instrumentation lifecycle

- **Two central gates**, both in `apps/mobile/utils/performance-debug.ts` and
  both requiring `__DEV__`:
  - `EXPO_PUBLIC_PERF_DEBUG=true` — timing, request, focus, count and
    lifecycle logs (milestones, requests, screen focus/blur, nav-tap, sheet,
    map, image samples, intent phases, fetch counts).
  - `EXPO_PUBLIC_PERF_RENDER_DEBUG=true` — per-component render counters
    **only** (`perfCountRender`). Split out after the smoke run showed render
    logging emits hundreds of lines per Discover load, distorting the very
    timings being measured. Normal timing benchmarks must run with this flag
    off; enable it only for dedicated re-render investigations.
- **Enable**: set the flag(s) in `apps/mobile/.env`, then restart Metro with
  `pnpm --filter @fomo/mobile start:clear`.
- **Disable**: remove the var(s) (or set `false`) and restart Metro the same
  way. Default state for both is **off**; `.env.example` documents both flags
  as `false`.
- **Release safety**: the `__DEV__` guard means release bundles never log,
  regardless of env.
- **Privacy**: no tokens, credentials, payloads or event-ID arrays are logged —
  endpoints are query-stripped and UUID-normalized; batches are logged as
  counts.
- Overhead when enabled is a handful of `console.log` calls per interaction
  (image sampling capped at 6, card render logs sampled 1/25); when disabled it
  is a boolean check.

---

## 15. Validation

- `pnpm --filter @fomo/mobile lint` — **pass** (expo lint, no findings).
- `@fomo/mobile` has **no `typecheck` script**; `pnpm --filter @fomo/mobile
  exec tsc --noEmit` — **pass**.
- There are **no automated mobile tests** in this repository (`"test": "echo
  'No tests yet'"`), and no automated performance tests. All benchmarking is
  the manual protocol in §12.
