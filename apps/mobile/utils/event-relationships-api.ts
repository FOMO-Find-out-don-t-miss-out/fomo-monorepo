import { apiFetchAuth } from './api-client';
import type { components } from '../types/api.generated';
import type { EventIntent } from '../types/ui';

export type RelationshipType = components['schemas']['RelationshipType'];
export type RelationshipResponse = components['schemas']['RelationshipResponse'];
export type EventRelationshipsResponse = components['schemas']['EventRelationshipsResponse'];
export type ApiEvent = components['schemas']['EventDiscoveryResponse'];

const BASE = '/api/v1/me';

// ── API boundary mapping ───────────────────────────────────────────────────────
//
// Mobile MVP: only `interested` and `going` exist. `saved` is ignored.

export function toEventIntent(types: RelationshipType[]): EventIntent {
  if (types.includes('going')) return 'going';
  if (types.includes('interested')) return 'interested';
  return null;
}

// ── Batch intent fetch ────────────────────────────────────────────────────────

export async function fetchEventIntents(
  eventIds: string[],
  accessToken: string,
): Promise<Record<string, EventIntent>> {
  if (eventIds.length === 0) return {};
  const qs = eventIds.map((id) => `event_ids=${encodeURIComponent(id)}`).join('&');
  const data = await apiFetchAuth<EventRelationshipsResponse>(
    `${BASE}/event-relationships?${qs}`,
    accessToken,
  );
  const result: Record<string, EventIntent> = {};
  for (const [id, types] of Object.entries(data.relationships)) {
    result[id] = toEventIntent(types as RelationshipType[]);
  }
  return result;
}

// ── Intent mutation ───────────────────────────────────────────────────────────
//
// Tap the active intent  → DELETE (toggle off) → returns null
// Tap a different intent → PUT   (switch)      → returns nextIntent
// Backend removes the opposite intent automatically on PUT.

export async function setEventIntent(
  eventId: string,
  currentIntent: EventIntent,
  nextIntent: 'interested' | 'going',
  accessToken: string,
): Promise<EventIntent> {
  const url = `${BASE}/events/${encodeURIComponent(eventId)}/relationships/${nextIntent}`;
  if (nextIntent === currentIntent) {
    await apiFetchAuth<void>(url, accessToken, { method: 'DELETE' });
    return null;
  }
  await apiFetchAuth<RelationshipResponse>(url, accessToken, { method: 'PUT' });
  return nextIntent;
}

// ── My Events list ────────────────────────────────────────────────────────────

export async function fetchMyEvents(
  relationshipType: RelationshipType,
  accessToken: string,
): Promise<ApiEvent[]> {
  return apiFetchAuth<ApiEvent[]>(
    `${BASE}/events?relationship_type=${encodeURIComponent(relationshipType)}`,
    accessToken,
  );
}
