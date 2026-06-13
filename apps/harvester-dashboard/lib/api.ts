import {
  PendingEvent,
  PendingEventUpdate,
  Venue,
  VenueUpdate,
  BatchApproveRequest,
  BatchRejectRequest,
  VenueMergeRequest,
  LocationBatchUpdate,
  OccurrenceCreate,
  GeocodeSuggestion,
  SuccessResponse,
  UserAdminResponse,
  UpdateSystemRoleRequest,
} from "../types/api";
import { getAccessToken, getUserManager } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

// Warn in the browser if the build arg was not injected — helps catch misconfigured builds early.
if (typeof window !== "undefined" && !API_BASE_URL) {
  console.error(
    "[harvester-dashboard] NEXT_PUBLIC_API_URL is not set. All API calls will fail.\n" +
    "For local dev: copy .env.example to .env.local and set NEXT_PUBLIC_API_URL.\n" +
    "For Docker: pass --build-arg NEXT_PUBLIC_API_URL=<url> to docker build."
  );
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    // Token expired mid-session — redirect to Keycloak unless already on an auth page
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth/")) {
      getUserManager().signinRedirect().catch(() => {});
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const moderationApi = {
  /**
   * Fetches pending events with optional filters
   */
  getPendingEvents: (locationName?: string, geocodingStatus?: string[]): Promise<PendingEvent[]> => {
    const params = new URLSearchParams();
    if (locationName) params.append("location_name", locationName);
    if (geocodingStatus) {
      geocodingStatus.forEach(status => params.append("geocoding_status", status));
    }
    const query = params.toString();
    return request<PendingEvent[]>(`/moderation/pending-events${query ? `?${query}` : ""}`);
  },

  /**
   * Fetches published events with optional filters
   */
  getPublishedEvents: (locationName?: string): Promise<PendingEvent[]> => {
    const params = new URLSearchParams();
    if (locationName) params.append("location_name", locationName);
    const query = params.toString();
    return request<PendingEvent[]>(`/moderation/events${query ? `?${query}` : ""}`);
  },

  /**
   * Unpublishes an event (moves it back to pending)
   */
  unpublishEvent: (eventId: string): Promise<SuccessResponse> => {
    return request<SuccessResponse>(`/moderation/events/${eventId}/unpublish`, {
      method: "POST",
    });
  },

  /**
   * Updates a single published event
   */
  updatePublishedEvent: (eventId: string, update: PendingEventUpdate): Promise<PendingEvent> => {
    return request<PendingEvent>(`/moderation/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  },

  /**
   * Updates a single pending event
   */
  updateEvent: (eventId: string, update: PendingEventUpdate): Promise<PendingEvent> => {
    return request<PendingEvent>(`/moderation/pending-events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  },

  /**
   * Approves a single event
   */
  approveEvent: (eventId: string): Promise<SuccessResponse> => {
    return request<SuccessResponse>(`/moderation/pending-events/${eventId}/approve`, {
      method: "POST",
    });
  },

  /**
   * Rejects a single event
   */
  rejectEvent: (eventId: string): Promise<SuccessResponse> => {
    return request<SuccessResponse>(`/moderation/pending-events/${eventId}/reject`, {
      method: "POST",
    });
  },

  /**
   * Approves multiple events in batch
   */
  approveBatch: (eventIds: string[]): Promise<SuccessResponse> => {
    return request<SuccessResponse>("/moderation/pending-events/approve-batch", {
      method: "POST",
      body: JSON.stringify({ event_ids: eventIds } as BatchApproveRequest),
    });
  },

  /**
   * Rejects multiple events in batch
   */
  rejectBatch: (eventIds: string[]): Promise<SuccessResponse> => {
    return request<SuccessResponse>("/moderation/pending-events/reject-batch", {
      method: "POST",
      body: JSON.stringify({ event_ids: eventIds } as BatchRejectRequest),
    });
  },

  /**
   * Adds a new occurrence (multi-day) for an event
   */
  addOccurrence: (eventId: string, startTime: string): Promise<PendingEvent> => {
    return request<PendingEvent>(`/moderation/pending-events/${eventId}/occurrences`, {
      method: "POST",
      body: JSON.stringify({ start_time: startTime } as OccurrenceCreate),
    });
  },

  /**
   * Fetches venues with search and verification filters
   */
  getVenues: (searchQuery?: string, onlyUnverified: boolean = false): Promise<Venue[]> => {
    const params = new URLSearchParams();
    if (searchQuery) params.append("search_query", searchQuery);
    if (onlyUnverified) params.append("only_unverified", "true");
    const query = params.toString();
    return request<Venue[]>(`/moderation/venues${query ? `?${query}` : ""}`);
  },

  /**
   * Updates venue details
   */
  updateVenue: (venueId: string, update: VenueUpdate): Promise<Venue> => {
    return request<Venue>(`/moderation/venues/${venueId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  },

  /**
   * Deletes a venue and unlinks its events
   */
  deleteVenue: (venueId: string): Promise<{ status: string }> => {
    return request<{ status: string }>(`/moderation/venues/${venueId}`, {
      method: "DELETE",
    });
  },

  /**
   * Merges a source venue into a target venue
   */
  mergeVenues: (sourceVenueId: string, targetVenueId: string): Promise<{ status: string }> => {
    return request<{ status: string }>("/moderation/venues/merge", {
      method: "POST",
      body: JSON.stringify({
        source_venue_id: sourceVenueId,
        target_venue_id: targetVenueId,
      } as VenueMergeRequest),
    });
  },

  /**
   * Performs a batch location update for all events matching a name
   */
  batchUpdateLocation: (data: LocationBatchUpdate): Promise<{ status: string }> => {
    return request<{ status: string }>("/moderation/batch-update-location", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * Gets geocoding suggestions from Mapbox via the backend
   */
  getMapboxSuggestions: (query: string, countryCode: string = "GR"): Promise<GeocodeSuggestion[]> => {
    const params = new URLSearchParams({ q: query, country_code: countryCode });
    return request<GeocodeSuggestion[]>(`/moderation/geocode/suggestions?${params.toString()}`);
  }
};

export const adminApi = {
  /** List all FOMO users, ordered newest first. Admin only. */
  getUsers: (): Promise<UserAdminResponse[]> =>
    request<UserAdminResponse[]>("/admin/users"),

  /** Update a user's system_role. Prevents self-demotion. Admin only. */
  updateUserRole: (userId: string, body: UpdateSystemRoleRequest): Promise<UserAdminResponse> =>
    request<UserAdminResponse>(`/admin/users/${userId}/system-role`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};
