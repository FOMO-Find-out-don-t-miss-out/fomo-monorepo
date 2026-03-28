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
  SuccessResponse
} from "../types/moderation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

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
    return request<{ status: string }>("/moderation/merge", {
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
