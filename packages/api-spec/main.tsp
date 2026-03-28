import "@typespec/http";
import "@typespec/rest";
import "@typespec/openapi3";

using TypeSpec.Http;
using TypeSpec.Rest;

@service(#{
  title: "FOMO API Service",
})
namespace Fomo;

@doc("Categories for events")
enum EventCategory {
  Music,
  Art,
  Tech,
  Food,
  Nightlife,
  Sports,
  Business,
  Community,
  Other,
}

@doc("The geocoding status of a location")
enum GeocodingStatus {
  verified,
  ambiguous,
  failed,
}

@doc("Metadata from geocoding providers")
model GeocodingMetadata {
  @doc("Confidence score of the geocoding result (0-1)")
  confidenceScore: float64;
  
  @doc("The geocoding status")
  status: GeocodingStatus;

  @doc("The name of the provider used for geocoding")
  provider?: string;

  @doc("Raw output from the geocoding provider")
  rawOutput?: Record<unknown>;

  @doc("Normalized address components")
  addressComponents?: Record<unknown>;
}

@doc("A real-time event discovery object")
model Event {
  @doc("Unique identifier")
  @key id: string;
  
  @doc("Event title")
  title: string;
  
  @doc("Detailed description")
  description?: string;
  
  @doc("UTC start time")
  startTime: utcDateTime;
  
  @doc("UTC end time")
  endTime?: utcDateTime;
  
  @doc("Event category")
  category: EventCategory;
  
  @doc("Specific sub-category")
  subCategory?: string;
  
  @doc("Hype or popularity score")
  hypeScore: int32;
  
  @doc("Direct ticket purchase URL")
  ticketUrl?: string;
  
  @doc("Original source URL")
  sourceUrl?: string;
  
  @doc("Human-readable location name")
  locationName?: string;
  
  @doc("ISO Country Code")
  countryCode?: string;
  
  @doc("Parent event ID for recurring or multi-day events")
  parentId?: string;
  
  @doc("Latitude")
  lat: float64;
  
  @doc("Longitude")
  lng: float64;
  
  @doc("URL to the event's promotional image")
  photoUrl?: string;
  
  @doc("Arbitrary metadata for the event")
  eventMetadata: Record<unknown>;
  
  @doc("List of tags associated with the event")
  tags: string[];

  @doc("Geocoding status")
  geocodingStatus: GeocodingStatus;

  @doc("Internal geocoding metadata (exposed only if requested)")
  geocodingMetadata?: GeocodingMetadata;
}

@doc("Response for event listing")
model EventList {
  items: Event[];
  total: int32;
}

@route("/events")
interface Events {
  @doc("List all available events")
  @get list(): EventList;
  
  @doc("Retrieve a single event by ID")
  @get read(@path id: string): Event | Error;
}

@doc("Standard error response")
model Error {
  code: int32;
  message: string;
}
