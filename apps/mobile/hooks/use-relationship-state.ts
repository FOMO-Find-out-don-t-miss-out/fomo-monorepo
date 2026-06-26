import { useCallback, useEffect, useRef, useState } from 'react';

import {
  markEventRelationship,
  removeEventRelationship,
  type RelationshipType,
} from '../utils/event-relationships-api';
import type { EventIntent } from '../types/ui';

// ─── API boundary mapping ─────────────────────────────────────────────────────

/** Map backend RelationshipType[] → EventIntent. `saved` is ignored in mobile MVP. */
export function toEventIntent(types: RelationshipType[]): EventIntent {
  if (types.includes('going')) return 'going';
  if (types.includes('interested')) return 'interested';
  return null;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UseRelationshipStateResult {
  /** Current intent state: event_id → EventIntent */
  state: Record<string, EventIntent>;
  /**
   * Merge server relationship data into the local state.
   * Maps RelationshipType[] → EventIntent at the API boundary.
   * Skips events with in-flight mutations to avoid stale responses overwriting
   * optimistic updates. Uses merge (not replace) so unrelated events survive.
   */
  syncFromServer: (serverState: Record<string, RelationshipType[]>) => void;
  /**
   * Toggle the intent for an event. If the given type is already active,
   * it is cleared (→ null). Otherwise it is set, and the backend atomically
   * removes any conflicting intent (interested ↔ going exclusivity).
   *
   * Applies an optimistic update and rolls back on API failure.
   * Toggle is stable (empty deps array) — safe to pass as a prop.
   */
  toggle: (eventId: string, type: 'interested' | 'going') => Promise<void>;
  /** True while a mutation for this event is in-flight. */
  isPending: (eventId: string) => boolean;
  /** Current EventIntent for an event (null if none or not yet hydrated). */
  intentFor: (eventId: string) => EventIntent;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useRelationshipState(
  accessToken: string | null,
): UseRelationshipStateResult {
  const [state, setState] = useState<Record<string, EventIntent>>({});
  const [pending, setPending] = useState<Set<string>>(new Set());

  // Refs so toggle/syncFromServer can read current values without being re-created.
  const stateRef = useRef(state);
  const pendingRef = useRef(pending);
  const tokenRef = useRef(accessToken);

  useEffect(() => { stateRef.current = state; }, [state]);
  useEffect(() => { pendingRef.current = pending; }, [pending]);
  useEffect(() => { tokenRef.current = accessToken; }, [accessToken]);

  const syncFromServer = useCallback(
    (serverState: Record<string, RelationshipType[]>) => {
      const updates: Record<string, EventIntent> = {};
      for (const [id, types] of Object.entries(serverState)) {
        // Never overwrite optimistic state for events with in-flight mutations.
        // A stale server response arriving after an optimistic update would
        // otherwise silently revert the user's action.
        if (!pendingRef.current.has(id)) {
          updates[id] = toEventIntent(types);
        }
      }
      setState((prev) => ({ ...prev, ...updates }));
    },
    [],
  );

  const toggle = useCallback(async (eventId: string, type: 'interested' | 'going') => {
    const token = tokenRef.current;
    if (!token) return;
    if (pendingRef.current.has(eventId)) return;

    const current = stateRef.current[eventId] ?? null;
    const isActive = current === type;
    const next: EventIntent = isActive ? null : type;

    if (__DEV__) {
      console.log('[intent] toggle', { eventId, type, current, next });
    }

    // Optimistic update
    setState((prev) => ({ ...prev, [eventId]: next }));
    setPending((prev) => new Set([...prev, eventId]));

    try {
      if (isActive) {
        await removeEventRelationship(eventId, type, token);
      } else {
        // Backend atomically removes any conflicting intent (interested ↔ going).
        await markEventRelationship(eventId, type, token);
      }
    } catch (err) {
      if (__DEV__) {
        console.warn('[intent] rollback', { eventId, type, current, err });
      }
      // Rollback to prior intent on failure.
      setState((prev) => ({ ...prev, [eventId]: current }));
    } finally {
      setPending((prev) => {
        const n = new Set(prev);
        n.delete(eventId);
        return n;
      });
    }
  }, []); // stable — reads current values via refs only

  const isPending = useCallback(
    (eventId: string) => pending.has(eventId),
    [pending],
  );

  const intentFor = useCallback(
    (eventId: string): EventIntent => state[eventId] ?? null,
    [state],
  );

  return { state, syncFromServer, toggle, isPending, intentFor };
}
