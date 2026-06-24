import { apiFetchAuth } from './api-client';
import type { components } from '../types/api.generated';

export type RelationshipType = components['schemas']['RelationshipType'];
export type RelationshipResponse = components['schemas']['RelationshipResponse'];
export type EventRelationshipsResponse = components['schemas']['EventRelationshipsResponse'];
export type ApiEvent = components['schemas']['EventDiscoveryResponse'];

const BASE = '/api/v1/me';

export async function fetchEventRelationshipState(
  eventIds: string[],
  accessToken: string,
): Promise<Record<string, RelationshipType[]>> {
  if (eventIds.length === 0) return {};
  const qs = eventIds.map((id) => `event_ids=${encodeURIComponent(id)}`).join('&');
  const data = await apiFetchAuth<EventRelationshipsResponse>(
    `${BASE}/event-relationships?${qs}`,
    accessToken,
  );
  return data.relationships;
}

export async function markEventRelationship(
  eventId: string,
  type: RelationshipType,
  accessToken: string,
): Promise<RelationshipResponse> {
  return apiFetchAuth<RelationshipResponse>(
    `${BASE}/events/${encodeURIComponent(eventId)}/relationships/${type}`,
    accessToken,
    { method: 'PUT' },
  );
}

export async function removeEventRelationship(
  eventId: string,
  type: RelationshipType,
  accessToken: string,
): Promise<void> {
  await apiFetchAuth<void>(
    `${BASE}/events/${encodeURIComponent(eventId)}/relationships/${type}`,
    accessToken,
    { method: 'DELETE' },
  );
}

export async function fetchMyEvents(
  relationshipType: RelationshipType,
  accessToken: string,
): Promise<ApiEvent[]> {
  return apiFetchAuth<ApiEvent[]>(
    `${BASE}/events?relationship_type=${encodeURIComponent(relationshipType)}`,
    accessToken,
  );
}

