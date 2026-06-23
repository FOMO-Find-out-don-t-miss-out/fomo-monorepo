import { useCallback, useEffect, useRef, useState } from 'react';

import {
  markEventRelationship,
  removeEventRelationship,
  type RelationshipType,
} from '../utils/event-relationships-api';

export interface UseRelationshipStateResult {
  /** Current merged relationship state: event_id → active relationship types */
  state: Record<string, RelationshipType[]>;
  /** Overwrite state with fresh server data (call after batch fetch completes) */
  syncFromServer: (serverState: Record<string, RelationshipType[]>) => void;
  /** Toggle a relationship type for an event, with optimistic update + rollback on failure */
  toggle: (eventId: string, type: RelationshipType) => Promise<void>;
  /** True while a specific (eventId, type) mutation is in-flight */
  isPending: (eventId: string, type: RelationshipType) => boolean;
  /** True if the given relationship type is currently active for an event */
  hasRelationship: (eventId: string, type: RelationshipType) => boolean;
}

/**
 * Manages optimistic relationship state for event cards and the detail sheet.
 *
 * Toggle is stable (empty deps) — it reads current values via refs to avoid
 * stale closures, so it is safe to pass as a prop without triggering re-renders.
 */
export function useRelationshipState(
  accessToken: string | null,
): UseRelationshipStateResult {
  const [state, setState] = useState<Record<string, RelationshipType[]>>({});
  const [pending, setPending] = useState<Set<string>>(new Set());

  // Refs so toggle can read current values without being re-created
  const stateRef = useRef(state);
  const pendingRef = useRef(pending);
  const tokenRef = useRef(accessToken);

  useEffect(() => { stateRef.current = state; }, [state]);
  useEffect(() => { pendingRef.current = pending; }, [pending]);
  useEffect(() => { tokenRef.current = accessToken; }, [accessToken]);

  const syncFromServer = useCallback(
    (serverState: Record<string, RelationshipType[]>) => setState(serverState),
    [],
  );

  const toggle = useCallback(async (eventId: string, type: RelationshipType) => {
    const token = tokenRef.current;
    if (!token) return;

    const key = `${eventId}:${type}`;
    if (pendingRef.current.has(key)) return;

    const current = stateRef.current[eventId] ?? [];
    const isActive = current.includes(type);
    const next = isActive ? current.filter((t) => t !== type) : [...current, type];

    // Optimistic update
    setState((prev) => ({ ...prev, [eventId]: next }));
    setPending((prev) => new Set([...prev, key]));

    try {
      if (isActive) {
        await removeEventRelationship(eventId, type, token);
      } else {
        await markEventRelationship(eventId, type, token);
      }
    } catch {
      // Rollback on failure
      setState((prev) => ({ ...prev, [eventId]: current }));
    } finally {
      setPending((prev) => {
        const n = new Set(prev);
        n.delete(key);
        return n;
      });
    }
  }, []); // stable — uses refs only

  const isPending = useCallback(
    (eventId: string, type: RelationshipType) => pending.has(`${eventId}:${type}`),
    [pending],
  );

  const hasRelationship = useCallback(
    (eventId: string, type: RelationshipType) => (state[eventId] ?? []).includes(type),
    [state],
  );

  return { state, syncFromServer, toggle, isPending, hasRelationship };
}
