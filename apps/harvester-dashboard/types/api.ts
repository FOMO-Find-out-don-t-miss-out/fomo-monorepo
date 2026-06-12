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

/**
 * Venue as returned by the API (backed by PlaceResponse schema).
 * id is always present on fetched records.
 * is_manually_verified is a dashboard-side convenience field; the backend
 * canonical field is verification_status === 'manually_verified'.
 */
export type Venue = Omit<components['schemas']['PlaceResponse'], 'id'> & {
  id: string;
  is_manually_verified?: boolean;
};
export type PendingEventUpdate = components['schemas']['PendingEventUpdate'];
export type VenueUpdate = components['schemas']['PlaceUpdate'] & {
  is_manually_verified?: boolean;
};
/** Merge request shape as sent by the dashboard API client (field names differ from PlaceMergeRequest). */
export interface VenueMergeRequest {
  source_venue_id: string;
  target_venue_id: string;
}
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

// ── Auth / user types ────────────────────────────────────────────────────────

/** FOMO internal user, including system_role for dashboard access control. */
export type UserMeResponse = components['schemas']['UserMeResponse'];

/** Role assigned to a FOMO user. admin > manager > moderator > user; service is isolated. */
export type UserSystemRole = components['schemas']['UserSystemRole'];

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
