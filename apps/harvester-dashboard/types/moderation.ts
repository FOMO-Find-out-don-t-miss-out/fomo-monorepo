export interface EventBase {
  title: string;
  start_time: string; // ISO Date string
  end_time?: string; // ISO Date string
  hype_score: number;
  category: string;
  sub_category?: string;
  ticket_url?: string;
  source_url?: string;
  location_name?: string;
  country_code?: string;
  parent_id?: string; // UUID
  photo_url?: string; // Computed property from metadata
  source_provider: string;
  ingestion_method: string;
}

export interface Event extends EventBase {
  id: string; // UUID
  location: unknown; // Geography POINT
  event_metadata: Record<string, unknown>;
  tags: string[];
}

export interface PendingEvent extends EventBase {
  id: string; // UUID
  location?: unknown; // Geography POINT
  event_metadata: Record<string, unknown>;
  tags: string[];
  status: 'pending' | 'published' | 'rejected';
  raw_content?: string;
  rejection_reason?: string;
  confidence_score?: number;
  geocoding_status: 'verified' | 'ambiguous' | 'failed';
  geocoding_metadata: Record<string, unknown>;
}

export interface Venue {
  id: string; // UUID
  name: string;
  country_code: string;
  city?: string;
  lat: number;
  lng: number;
  full_address: string;
  relevance: number;
  is_manually_verified: boolean;
  created_at: string; // ISO Date string
}

export interface PendingEventUpdate {
  title?: string;
  start_time?: string;
  end_time?: string;
  location_name?: string;
  category?: string;
  hype_score?: number;
  ticket_url?: string;
  event_metadata?: Record<string, unknown>;
}

export interface VenueUpdate {
  name?: string;
  city?: string;
  full_address?: string;
  lat?: number;
  lng?: number;
  is_manually_verified?: boolean;
}

export interface BatchApproveRequest {
  event_ids: string[]; // UUIDs
}

export interface BatchRejectRequest {
  event_ids: string[]; // UUIDs
}

export interface VenueMergeRequest {
  source_venue_id: string; // UUID
  target_venue_id: string; // UUID
}

export interface LocationBatchUpdate {
  target_name: string;
  lat: number;
  lng: number;
  status: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface OccurrenceCreate {
  start_time: string; // ISO Date string
}

export interface GeocodeSuggestion {
  lat: number;
  lng: number;
  relevance: number;
  full_address: string;
  country_code: string;
  city?: string;
  geocoding_status: string;
  geocoding_metadata: Record<string, unknown>;
}

export interface SuccessResponse {
  status: string;
  approved_count?: number;
  rejected_count?: number;
}
