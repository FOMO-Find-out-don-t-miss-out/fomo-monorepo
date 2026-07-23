# Mobile Performance Baseline & Responsiveness RCA (FOMO-174)

Status: **instrumentation complete; five-run physical-device debug baseline
captured; release comparison and device/network metadata pending**.
App commit at time of audit: `74e40e3` (plus the FOMO-174 instrumentation changes).

This document separates these classes of statements throughout:

- **[MEASURED — DEBUG PHYSICAL DEVICE, N=5]** — the completed repeated
  baseline (§4): five clean timing runs on the physical Android device,
  debug build, Metro attached, `EXPO_PUBLIC_PERF_DEBUG=true`,
  `EXPO_PUBLIC_PERF_RENDER_DEBUG=false` (render-counter observer overhead
  disabled). Reported as median / min / max; no p95 is computed from five
  samples. These numbers characterize the **debug build** — production
  severity is still gated on the release comparison.
- **[MEASURED — SMOKE]** — the earlier 1–2-sample sanity pass (§1a), captured
  **with render logging enabled**; superseded by the N=5 baseline for all
  timing purposes, retained for the render-count evidence.
- **[STATIC]** — directly observable in the committed source code (file/line
  cited). These are facts about what the code does, not about how slow it is.
- **[HYPOTHESIS]** — a plausible performance consequence of a static finding
  that still requires measurement before it may be called a bottleneck.

---

## 1. Executive summary

The app is small (4 tab screens, ~20 components) and its data layer is plain
`fetch` + `useState` hooks with no cache. The five-run debug baseline (§4) has
now confirmed and quantified the picture, in **measured debug-build impact
order**:

1. **Discover rendering is the strongest confirmed bottleneck.** The initial
   discovery request costs only 289 ms (median), while *parsed events →
   cards rendered* costs **1659 ms** (median): the JS/rendering side dwarfs
   the network side. The non-virtualized carousel mounts all 70 returned
   cards in all 5/5 runs ([MEASURED — DEBUG PHYSICAL DEVICE, N=5], §4/§6).
2. **The duplicate location-driven startup cycle is confirmed.** Two discovery
   HTTP requests occurred in 5/5 runs, and 4/5 runs executed a complete
   duplicate render + intent-fetch cycle, pushing *focus → fully settled* to
   ~5.9 s median in those runs (§5).
3. **The full 70-ID intent synchronization policy is confirmed as frequent and
   costly**: `id_batch=70` / `query_len=3290` on every sync; the startup
   intent request measured 1270 ms median (with a JS-thread-contention caveat,
   §5); Discover refocus alone costs ~1153 ms to refreshed intent state (§4).
4. **Intent actions settle the mutation in ~617 ms but need ~1797 ms until
   full reconciliation** because a full-batch refetch follows the mutation
   (~593 ms gap between mutation completion and refetch start) (§4/§5).
5. **Auth boot remains a confirmed long critical path**: bootstrap 1339 ms
   median (refresh exchange 564 ms + `/users/me` 532 ms, sequential); JS init →
   auth gate resolved 3170 ms median. Final severity needs the release
   comparison (§4).
6. **Duplicate My Events requests are confirmed**: four `GET /me/events` calls
   on first focus in 5/5 runs — double the expected count (§5).
7. **My Events replaces its list with a full-screen spinner on every focus**
   ([STATIC], §6) — unchanged, still a guaranteed visible defect.
8. **Cleared as primary suspects** by the measurements: Event Details opening
   (178/306 ms), tab navigation (45–90 ms), and map remounting (§4).

Debug-build overhead (Metro, dev-mode JS, dev Mapbox/Reanimated/BlurView)
inflates all of the above by an unknown factor — the release comparison (§8)
is the remaining step before production-severity conclusions.

---

## 1a. Preliminary physical-device smoke results [MEASURED — SMOKE]

> **Superseded for timing purposes** by the five-run baseline in §4 (which was
> captured with render logging off). This section is retained because it holds
> the only render-count evidence (~350 EventCard renders per load/interaction),
> which the N=5 timing runs deliberately did not re-capture.

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

Environment of the completed five-run debug baseline (§4). Fields not supplied
with the run data remain **pending** and must be recorded before the report is
finalized:

| Field | Value |
| ----- | ----- |
| Device model | **pending** (not recorded with the run data) |
| Android version | **pending** (not recorded with the run data) |
| Build type | debug |
| Metro attached | yes |
| JS debugger / DevTools open | not recorded — assumed no; confirm |
| Network | **pending** (not recorded; same network across all 5 runs per protocol) |
| API environment | staging |
| App commit | FOMO-174 instrumentation branch (post-`4e751dc`) |
| `EXPO_PUBLIC_PERF_DEBUG` | true |
| `EXPO_PUBLIC_PERF_RENDER_DEBUG` | false (render observer overhead disabled) |
| Runs | 5 clean timing runs |

The release-comparison environment table is entirely pending.

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

## 4. Results table [MEASURED — DEBUG PHYSICAL DEVICE, N=5]

Five clean timing runs, debug build, Metro attached, staging API, render
logging **off** (`EXPO_PUBLIC_PERF_RENDER_DEBUG=false`). Median / min / max;
no p95 from five samples. All "JS init" metrics start at JS-bundle evaluation,
not native process launch (§3). Stopwatch icon→first-frame cold start was not
part of this capture and remains pending.

### Startup

| Metric | Runs | Median | Min | Max |
| ------ | ---: | -----: | --: | --: |
| JS init → root layout mounted | 5 | 352 ms | 350 ms | 359 ms |
| JS init → fonts ready | 5 | 1601 ms | 1512 ms | 2265 ms |
| Auth bootstrap duration | 5 | 1339 ms | 1108 ms | 1400 ms |
| JS init → auth gate resolved (first usable screen) | 5 | 3170 ms | 2914 ms | 3896 ms |
| Keycloak refresh exchange | 5 | 564 ms | 284 ms | 638 ms |
| `GET /users/me` | 5 | 532 ms | 486 ms | 579 ms |

### Discover

| Metric | Runs | Median | Min | Max |
| ------ | ---: | -----: | --: | --: |
| Initial discovery request | 5 | 289 ms | 260 ms | 336 ms |
| Discover focus → first cards rendered | 5 | 1910 ms | 1805 ms | 2128 ms |
| Discovery events parsed → cards rendered | 5 | 1659 ms | 1573 ms | 1720 ms |
| Discover focus → last startup render | 5 | 4633 ms | 2128 ms | 4878 ms |
| Discover focus → startup fully settled | 5 | 5916 ms | 3553 ms | 6040 ms |
| Initial startup intent request (`id_batch=70`) | 5 | 1270 ms | 1229 ms | 1427 ms |
| Map style loaded | 5 | 645 ms | 572 ms | 665 ms |

The wide min–max spread on "last startup render" / "fully settled" reflects
the duplicate startup cycle occurring in 4/5 runs (§5): in the four
duplicate-cycle runs, focus → fully settled was ~5925 ms median
(range 5809–6040 ms); the single run without the duplicated render/intent
cycle settled at the 3553 ms minimum.

### Event Details / intent actions

| Metric | Runs | Median | Min | Max |
| ------ | ---: | -----: | --: | --: |
| Event sheet open → `Modal.onShow` | 5 | 178 ms | 160 ms | 225 ms |
| Event sheet open → animation complete | 5 | 306 ms | 306 ms | 308 ms |
| Intent mutation settled | 5 | 617 ms | 610 ms | 625 ms |
| Mutation completion → follow-up refetch start | 5 | 593 ms | 564 ms | 610 ms |
| Follow-up intent refetch request | 5 | 584 ms | 573 ms | 607 ms |
| Intent tap → full reconciliation | 5 | 1797 ms | 1773 ms | 1802 ms |

### Navigation / My Events / Discover refocus

| Metric | Runs | Median | Min | Max |
| ------ | ---: | -----: | --: | --: |
| My Events tab tap → focus | 5 | 90 ms | 88 ms | 96 ms |
| My Events focus → stable list | 5 | 404 ms | 353 ms | 477 ms |
| My Events tab tap → stable list | 5 | 500 ms | 444 ms | 567 ms |
| Return to Discover tab tap → focus | 5 | 45 ms | 43 ms | 46 ms |
| Discover refocus → intent fetch start | 5 | 562 ms | 560 ms | 570 ms |
| Discover refocus intent request | 5 | 583 ms | 495 ms | 602 ms |
| Discover refocus → refreshed intent state | 5 | 1153 ms | 1056 ms | 1165 ms |

### Additional measured facts (all 5 runs unless stated)

- Discovery returned **70 events** and `cards_rendered=70` in 5/5 runs.
- **Two** discovery HTTP requests occurred in 5/5 runs; a **complete duplicate
  render + intent-fetch cycle** followed in 4/5 runs (in the fifth, both
  discovery requests fired but only one result proceeded to render + intent
  fetch).
- Intent batch requests always carried `id_batch=70`, `query_len=3290`.
- **Four** `GET /api/v1/me/events` requests on first My Events focus in 5/5 runs.

### Still pending

| Flow | Build | Status |
| ---- | ----- | ------ |
| Cold app start (icon → first frame, stopwatch) | debug | Pending physical-device run |
| Warm start | debug | Pending physical-device run |
| All flows | release | Pending physical-device run (stopwatch/recording only) |

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

### Largest ID batches / query strings [MEASURED — DEBUG PHYSICAL DEVICE, N=5]

`fetchEventIntents` builds one `event_ids=<uuid>` pair per loaded event
(`utils/event-relationships-api.ts:29`), re-sent on **every** Discover focus
and after every intent toggle. Confirmed across all five runs: every intent
request carried `id_batch=70`, `query_len=3290`. Durations: startup intent
request **1270 ms median (1229–1427 ms)**; Discover-refocus intent request
**583 ms median (495–602 ms)**; post-mutation refetch **584 ms median**.

- The batch always covers **all events returned by the discovery API** — not
  just visible cards (`eventIds` is built from the full `eventsWithDistance`
  array, `app/(tabs)/index.tsx:95`).
- **Attribution nuance — do not read the 1.2–1.4 s startup figure as backend
  time.** These are JavaScript-observed `fetch` timings: the duration includes
  any promise-continuation delay while the JS thread is busy mounting and
  re-rendering 70 cards. In several runs the second discovery response and the
  intent response were logged at the **same timestamp**, indicating JS-thread
  scheduling contention rather than genuinely slow responses. The refocus
  figure (~583 ms, taken when the JS thread is quiet) is the better estimate
  of the request's true network+server cost; the startup figure measures how
  long the app *waits* for intent state, which is the user-relevant number
  either way.

### Duplicates / races

- Startup double discovery fetch — **confirmed** [MEASURED — DEBUG PHYSICAL
  DEVICE, N=5]: two discovery HTTP requests in **5/5 runs**; a complete
  duplicate render + intent-fetch cycle followed in **4/5 runs** (in the
  fifth run only one result proceeded to render + intent fetch). In the four
  full-duplicate runs, Discover focus → fully settled was ~5925 ms median
  (5809–6040 ms) versus 3553 ms in the single non-duplicated run — i.e. the
  duplicate cycle roughly **adds ~2.4 s of settle time** in the debug build.
  Both hooks have correct `cancelled` cleanup, so no stale-state corruption —
  the cost is pure wasted work.
- **Four** `GET /api/v1/me/events` calls on first My Events focus —
  **confirmed in 5/5 runs** [MEASURED — DEBUG PHYSICAL DEVICE, N=5]: two per
  relationship type, double the expected count. Attribution (mount-time hook
  effect + focus-refetch tick both firing, `use-my-events.ts` +
  `saved.tsx:135-137`) is consistent with the code but has not been verified
  with cycle-correlated logs.
- `useEffect(() => setLocalIntents({}), [serverIntents])`
  (`app/(tabs)/index.tsx:108-110`) fires an extra state update after **every**
  intents response, even a no-op one, because `serverIntents` is always a new
  object → one extra full-screen render per intents fetch.
- No request cancellation/abort exists (no `AbortController`); slow requests
  run to completion.

### Longest requests [MEASURED — DEBUG PHYSICAL DEVICE, N=5]

1. Startup intent batch — 1270 ms median (JS-observed; contention caveat above).
2. Intent mutation (`PUT`/`DELETE`) — 617 ms median.
3. Intent refetch (refocus / post-mutation) — 583–584 ms median.
4. Keycloak refresh exchange — 564 ms median.
5. `GET /users/me` — 532 ms median.
6. Initial discovery request — 289 ms median (the *cheapest* major request —
   the payload/query concern from the static audit is on the intents endpoint,
   not discovery).

---

## 6. Rendering analysis

**Rendering is the strongest confirmed debug-build bottleneck**
[MEASURED — DEBUG PHYSICAL DEVICE, N=5]: the initial discovery request costs
289 ms median while *events parsed → cards rendered* costs **1659 ms median
(1573–1720 ms)** — roughly **5–6× the network cost** is spent in JS/render
work before the user sees cards. Items without a measured tag below remain
[STATIC] observations.

**Discover screen (`app/(tabs)/index.tsx`)**
- The carousel is a plain horizontal `ScrollView` mapping over
  `filteredEvents` — **no virtualization**: every event becomes a mounted
  `EventCard`, and every card image starts downloading immediately
  (`index.tsx:274-293`). [MEASURED — DEBUG PHYSICAL DEVICE, N=5]:
  `cards_rendered=70` of 70 events in **5/5 runs** — all cards mount.
- [MEASURED — SMOKE, render-count evidence]: the `EventCard` render counter
  reached ~350 during one initial Discover load (≈ five full 70-card render
  passes), and a single intent interaction added another ~350 while also
  re-rendering `DiscoverScreen`, `FomoMap`, `EventDetails` and
  `IntentSelector` — the whole-tree re-render fan-out is real. The N=5 runs
  corroborate the load-time consequence without render logging: *focus → last
  startup render* was 4633 ms median, i.e. render passes continue for seconds
  after the first cards appear (duplicate startup cycle, intent-state arrival,
  `localIntents` clear).
- JS-thread saturation is directly visible in the N=5 request logs: intent
  responses were logged at the same timestamp as the second discovery response
  in several runs — network completions queue behind card mounting (§5 nuance).
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
  stack. [MEASURED — DEBUG PHYSICAL DEVICE, N=5]: `style-loaded` at 645 ms
  median (572–665 ms) after mount, and no second `style-loaded` after leaving
  and returning to Discover — **map remounting is ruled out** as a suspect.
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

The five-run debug baseline promotes the RCA from preliminary to **confirmed
(debug build)**. "Confirmed (debug)" means: mechanism verified in code AND
magnitude measured across five clean runs on the physical device. **Production
severity remains open for every row until the release comparison** — dev-mode
overhead inflates all magnitudes by an unknown factor. Rows are ordered by
measured debug-build impact.

| # | Symptom | Root cause (mechanism) | Evidence | Confidence | Affected flows | Recommended fix (follow-up) |
| - | ------- | ---------------------- | -------- | ---------- | -------------- | --------------------------- |
| 1 | Cards appear ~1.9 s after Discover focus although the API answered in ~0.3 s | Non-virtualized carousel mounts all 70 cards; JS/render work dominates (parsed→rendered 1659 ms vs request 289 ms); network completions queue behind mounting | [STATIC] `index.tsx:274-293` + [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §4/§6 | **confirmed (debug)** | Discover initial load | T3, T2, T4 |
| 2 | Startup takes ~5.9 s to fully settle in most runs | Location-driven duplicate discovery fetch triggers a complete second render + intent-fetch cycle (4/5 runs; ~+2.4 s settle vs the non-duplicated run) | [STATIC] `use-discovery.ts:53` + [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §5 | **confirmed (debug)** | Cold start → Discover | T1/T5 |
| 3 | Network chatter + ~1.2 s wait for intent state on every Discover entry | Unconditional full-batch intent sync for all loaded events: `id_batch=70`/`query_len=3290` every time; startup 1270 ms median (JS-contention caveat §5), refocus 583 ms, refocus→refreshed state 1153 ms | [STATIC] `index.tsx:115-119` + [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §5 | **confirmed (debug)** | Discover focus/refocus, intent toggle | T1 |
| 4 | Intent tap takes ~1.8 s to fully reconcile (mutation itself 617 ms) | Server-authoritative toggle followed by a full 70-ID refetch; ~593 ms gap between mutation completion and refetch start (JS busy re-rendering) | [STATIC] `index.tsx:121-150`, `saved.tsx:157-183` + [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §4 | **confirmed (debug)** | Interested/Going | T6, T1 |
| 5 | ~3.2 s from JS init to first usable screen | Fully sequential auth chain: refresh exchange 564 ms + `/users/me` 532 ms + SecureStore I/O, all blocking AuthGate | [STATIC] `auth-provider.tsx:127-165` + [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §4 | **confirmed (debug)**; final severity needs release comparison | Cold/warm start | T5 |
| 6 | Doubled My Events network cost on first focus | Four `GET /me/events` instead of two in 5/5 runs; attribution (mount effect + focus tick) consistent with code, not yet cycle-correlated | [MEASURED — DEBUG PHYSICAL DEVICE, N=5] §5 | **confirmed (debug)**, source attribution pending | My Events first focus | T7 |
| 7 | Content flash/spinner on every My Events visit | Refetch-on-focus discards the rendered list while loading | [STATIC] `saved.tsx:283-291`; flash mechanism needs no timing | **high** | My Events focus | T7 |
| 8 | Whole-tree re-renders on any Discover state change | Unmemoized cards + inline callbacks + screen-level state (incl. `localIntents` clear after every intents response) | [STATIC] §6 + [MEASURED — SMOKE render counts] ~350 EventCard renders per load and per interaction | **confirmed mechanism** (counts from the smoke pass; timing consequence folded into rows 1 and 4) | Discover interactions | T2 |
| 9 | Everything is slower than production will be | Dev-mode JS + Metro + dev Mapbox/Reanimated/Blur | [STATIC] build config; magnitude **pending release run** | high that it exists, magnitude pending | all | T8 |

Cleared by the N=5 baseline: Event Details opening (178 ms to visible, 306 ms
to animation end), tab navigation (45–90 ms tap→focus), and map remounting (no
repeat `style-loaded`; 645 ms initial load). My Events focus→stable list
(404 ms median) is unremarkable apart from rows 6–7.

---

## 10. Top bottlenecks — final debug-build ranking [MEASURED — DEBUG PHYSICAL DEVICE, N=5]

This ranking is final **for the debug build**. Production ranking is pending
the release comparison; the relative order of JS/render-bound items (1, 2, 4)
versus network-bound items (3, 5) may shift once dev-mode JS overhead is
removed. Cleared suspects: Event Details opening, tab navigation, map
remounting (§9).

1. **Discover render path** (RCA #1): 1659 ms from parsed events to rendered
   cards versus a 289 ms API request — the JS/render side is ~5–6× the network
   side, on the app's most important screen.
2. **Duplicate location-driven startup cycle** (RCA #2): doubles discovery +
   intent work in 4/5 runs and adds roughly 2.4 s to a ~5.9 s settle time.
3. **Full 70-ID intent synchronization policy** (RCA #3): runs on every
   Discover entry and after every toggle; 583–1270 ms per sync, 1153 ms
   refocus→refreshed state.
4. **Intent action reconciliation** (RCA #4): ~1.8 s tap→settled against a
   617 ms mutation — most of the wait is the follow-up full-batch refetch plus
   JS-thread contention.
5. **Sequential auth boot** (RCA #5): 3170 ms JS init→usable screen; two
   sequential network round-trips are structural, but severity vs release
   build still unknown.

---

## 11. Quick wins (small, low-risk; NOT implemented in this task)

| Quick win | Expected impact | Effort | Risk | Evidence |
| --------- | --------------- | ------ | ---- | -------- |
| Don't fetch discovery until location status resolves (or short grace window) | removes the duplicate cold-start cycle measured at ~+2.4 s settle time in 4/5 runs | S | low-med (delays first paint if location is slow — weigh against the measured 2.4 s) | RCA #2, §5 |
| Skip intents refetch on focus when the ID set is unchanged **and** last fetch is fresh (<X s) | removes a 583 ms request + ~1153 ms refresh cycle per Discover re-entry | S–M | low-med (staleness window) | RCA #3, §4 |
| `React.memo` on `EventCard` / `MyEventListItem` + stable `onPress` (e.g. pass `id`) | cuts the measured ~350-render/70-card passes per load and per interaction | S | low | RCA #8, §6 |
| Skip `setLocalIntents({})` when already empty (or compare keys) | one fewer full-screen render (≈ one 70-card pass) per intents response | S | low | RCA #8, §5 |
| Keep previous My Events list visible during refetch (don't flip to spinner when data exists) | removes a guaranteed flash per focus | S | low | RCA #7 |
| Debounce `onSearchChange` or keep text state inside `SearchBar` | avoids whole-screen (incl. map) render per keystroke | S | low | RCA #8, §6 |

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

All tickets below are now supported by confirmed (debug) N=5 evidence.

- **T1 — Optimize Discover intent fetching**: refetch on focus only when the
  ID set changed or data is stale; the measured `query_len=3290` / 583–1270 ms
  per sync justifies also considering a smaller batch or a POST body; fold in
  the location-resolution double-fetch fix (measured at ~+2.4 s settle).
- **T2 — Cut Discover re-render fan-out**: memoize `EventCard`, stabilize
  callbacks, localize search-text state, guard the `localIntents` clear.
- **T3 — Virtualize/window the Discover carousel** (horizontal `FlatList`
  with tuned `initialNumToRender`/`windowSize`) — keep the same visuals.
  Primary target of the 1659 ms parsed→rendered finding.
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

The debug baseline is complete; ordering now reflects measured debug impact,
with one remaining measurement gate up front:

1. **Run the release comparison** (§8, §12 step 12) — the only measurement
   still needed for production-severity conclusions. JS/render-bound items
   (T2/T3) are the most likely to shrink in release; do not start heavy render
   work before seeing these numbers.
2. **T1** (intent refetch policy + duplicate-startup-cycle fix) — highest
   measured impact that is *not* expected to deflate much in release: it
   removes whole requests and a duplicated work cycle (~+2.4 s settle,
   583–1270 ms per sync), which no build type gives back.
3. **T7** (My Events refresh strategy + duplicate first-focus requests) —
   smallest certain win; also do the cycle-correlation to close RCA #6's
   attribution.
4. **T2 → T3 → T4** (Discover rendering/images), scaled by what the release
   run shows for the 1659 ms parsed→rendered figure: memoization first (cheap,
   de-risks the FlatList migration), virtualization second, images last (they
   depend on backend resize capabilities).
5. **T5** (auth boot) — bounded, isolated; the two sequential round-trips are
   structural and survive the release build, but re-rank after step 1.
6. **T6** (optimistic intents) — biggest perceived-latency win on the intent
   path (~1.8 s → instant feedback), but a product-behavior change that needs
   sign-off.
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
