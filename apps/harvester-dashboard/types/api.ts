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
 * id is always present on fetched records. Verification state lives in
 * verification_status; use isPlaceVerified() from lib/utils to read it.
 */
export type Venue = Omit<components['schemas']['PlaceResponse'], 'id'> & {
  id: string;
};
export type PendingEventUpdate = components['schemas']['PendingEventUpdate'];
/** FOMO-16 collision-detection bucket persisted on a pending event. */
export type DedupeStatus = components['schemas']['DedupeStatus'];
export type VenueUpdate = components['schemas']['PlaceUpdate'];
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

// ── Admin user management types (FOMO-157, FOMO-161) ────────────────────────

/** User record returned by admin management endpoints. */
export type UserAdminResponse = components['schemas']['UserAdminResponse'];

/** Request body for PATCH /admin/users/{user_id}/system-role. */
export type UpdateSystemRoleRequest = components['schemas']['UpdateSystemRoleRequest'];

/** Request body for POST /admin/users/invite. */
export type InviteUserRequest = components['schemas']['InviteUserRequest'];

/** Response for POST /admin/users/invite. Includes keycloak_created flag. */
export type InviteUserResponse = components['schemas']['InviteUserResponse'];

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
