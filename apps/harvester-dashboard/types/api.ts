/**
 * Named type aliases over the auto-generated OpenAPI schema types.
 * Import from here, NOT from api.generated.ts directly.
 * Regenerate the underlying file with: pnpm --filter @fomo/harvester-dashboard generate:types
 */
import type { components } from './api.generated';

// ── Core domain types ────────────────────────────────────────────────────────

/** Pending event as returned by the moderation API. */
export type PendingEvent = Omit<
  components['schemas']['PendingEventResponse'],
  'status'
> & {
  status: 'pending' | 'published' | 'rejected';
};

/** Venue as returned by the API. id is always present on fetched records. */
export type Venue = Omit<components['schemas']['Venue'], 'id'> & { id: string };
export type PendingEventUpdate = components['schemas']['PendingEventUpdate'];
export type VenueUpdate        = components['schemas']['VenueUpdate'];
export type VenueMergeRequest  = components['schemas']['VenueMergeRequest'];
export type LocationBatchUpdate = components['schemas']['LocationBatchUpdate'];
export type BatchApproveRequest = components['schemas']['BatchApproveRequest'];
export type BatchRejectRequest  = components['schemas']['BatchRejectRequest'];
export type OccurrenceCreate   = components['schemas']['OccurrenceCreate'];

/**
 * Geocode suggestion from the Mapbox suggestions endpoint.
 * lat/lng are narrowed to non-null because the API only returns suggestions
 * that have resolved coordinates.
 */
export type GeocodeSuggestion = Omit<
  components['schemas']['GeocodeResult'],
  'lat' | 'lng' | 'geocoding_metadata'
> & {
  lat: number;
  lng: number;
  geocoding_metadata: { [key: string]: unknown };
};

// ── Types not yet declared as named schemas in FastAPI ───────────────────────

/**
 * Generic success response returned by approve/reject/unpublish mutations.
 * The API returns this shape but it is not exposed as a named OpenAPI schema.
 */
export interface SuccessResponse {
  status: string;
  approved_count?: number;
  rejected_count?: number;
}
