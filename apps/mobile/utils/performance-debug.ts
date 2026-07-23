// Central, gated performance instrumentation (FOMO-174).
//
// Two independent gates, both requiring __DEV__ (never active in a release
// bundle):
//
//   EXPO_PUBLIC_PERF_DEBUG=true         — timing, request, focus, count and
//                                         lifecycle logs (milestones, requests,
//                                         screen focus, sheet/map/image timing,
//                                         intent phases).
//   EXPO_PUBLIC_PERF_RENDER_DEBUG=true  — per-component render counters ONLY.
//                                         Kept separate because logging every
//                                         render adds measurable observer
//                                         overhead (a smoke run showed ~350
//                                         EventCard renders during one Discover
//                                         load) that would distort the timing
//                                         logs above. OFF by default; enable
//                                         only for dedicated re-render
//                                         investigations, never during timing
//                                         benchmark runs.
//
// Enable:  add the flag(s) to apps/mobile/.env, restart Metro with
//          `pnpm --filter @fomo/mobile start:clear` (env vars are inlined at
//          bundle time).
// Disable: remove the var (or set it to anything other than "true") and
//          restart Metro the same way.
//
// Log contract: single-line, `[perf]` prefix, key=value pairs. Never log
// tokens, credentials, payloads, or raw event-ID arrays — counts only.

import { useFocusEffect } from 'expo-router';
import { useCallback } from 'react';

const PERF_DEBUG =
  __DEV__ && process.env.EXPO_PUBLIC_PERF_DEBUG === 'true';

const PERF_RENDER_DEBUG =
  __DEV__ && process.env.EXPO_PUBLIC_PERF_RENDER_DEBUG === 'true';

export const perfEnabled: boolean = PERF_DEBUG;
export const perfRenderEnabled: boolean = PERF_RENDER_DEBUG;

type PerfFields = Record<string, string | number | boolean | null | undefined>;

// performance.now() when available (monotonic), Date.now() otherwise.
function now(): number {
  const perf = (globalThis as { performance?: { now?: () => number } }).performance;
  return typeof perf?.now === 'function' ? perf.now() : Date.now();
}

// Timestamp of JS evaluation of this module. This is NOT native process launch:
// metrics derived from it start when the JS bundle begins executing (after
// native init + bundle download in dev). Milestone logs name this explicitly.
const JS_INIT_TS = now();

function formatFields(fields: PerfFields): string {
  return Object.entries(fields)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}=${v}`)
    .join(' ');
}

/** Structured perf log line: `[perf] flow=<flow> k=v ...` */
export function perfLog(flow: string, fields: PerfFields = {}): void {
  if (!PERF_DEBUG) return;
  console.log(`[perf] flow=${flow} ${formatFields(fields)}`.trimEnd());
}

/** Monotonic mark for manual duration measurement. Returns 0 when disabled. */
export function perfMark(): number {
  return PERF_DEBUG ? now() : 0;
}

/** Milliseconds elapsed since a perfMark(), rounded. */
export function perfSince(mark: number): number {
  return PERF_DEBUG ? Math.round(now() - mark) : 0;
}

/**
 * App-lifecycle milestone, reported relative to JS-bundle init of this module
 * (metric name: t_since_js_init_ms — accurate name, not "app launch").
 */
export function perfMilestone(name: string, fields: PerfFields = {}): void {
  if (!PERF_DEBUG) return;
  perfLog('milestone', {
    name,
    t_since_js_init_ms: Math.round(now() - JS_INIT_TS),
    ...fields,
  });
}

// ── Correlation cycles ────────────────────────────────────────────────────────
// One counter per flow name; used to correlate the burst of logs caused by a
// single screen focus / interaction.

const cycleCounters: Record<string, number> = {};

export function perfNextCycle(flow: string): number {
  if (!PERF_DEBUG) return 0;
  cycleCounters[flow] = (cycleCounters[flow] ?? 0) + 1;
  return cycleCounters[flow];
}

// ── Render counters ───────────────────────────────────────────────────────────

const renderCounters: Record<string, number> = {};

/**
 * Call unconditionally at the top of a component body. Increments a per-name
 * render counter; logs every render, or every `sampleEvery`-th render for
 * high-cardinality components (e.g. list cards).
 * Not a React hook — no hook calls inside — so it is safe anywhere.
 *
 * Gated by EXPO_PUBLIC_PERF_RENDER_DEBUG (NOT the main timing flag): render
 * logging is high-volume observer overhead and must stay silent during timing
 * benchmark runs.
 */
export function perfCountRender(name: string, sampleEvery = 1): void {
  if (!PERF_RENDER_DEBUG) return;
  const count = (renderCounters[name] = (renderCounters[name] ?? 0) + 1);
  if (count === 1 || count % sampleEvery === 0) {
    console.log(`[perf] flow=render component=${name} count=${count}`);
  }
}

// ── Screen focus/blur logging ────────────────────────────────────────────────

/**
 * Logs focus/blur of a tab screen with a per-screen cycle counter and a raw
 * monotonic timestamp `t` (same clock as nav-tap logs, for computing
 * tab-press → focus latency). Call once at the top of a screen component.
 */
export function usePerfScreenFocus(screen: string): void {
  useFocusEffect(
    useCallback(() => {
      if (!PERF_DEBUG) return;
      const cycle = perfNextCycle(`${screen}-focus`);
      perfLog('screen-focus', { screen, cycle, t: Math.round(now()) });
      return () => {
        perfLog('screen-blur', { screen, cycle, t: Math.round(now()) });
      };
    }, [screen]),
  );
}

// ── Image-load sampling ───────────────────────────────────────────────────────
// Cap instrumented images per session so the measurement itself stays cheap.

const IMAGE_SAMPLE_CAP = 6;
let imageSampleCount = 0;

/** Reserve an image-timing sample slot; returns a slot id or null when full/disabled. */
export function perfClaimImageSample(): number | null {
  if (!PERF_DEBUG) return null;
  if (imageSampleCount >= IMAGE_SAMPLE_CAP) return null;
  imageSampleCount += 1;
  return imageSampleCount;
}
