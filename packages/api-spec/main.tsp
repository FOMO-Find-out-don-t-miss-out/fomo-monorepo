import "@typespec/http";
import "@typespec/rest";
import "@typespec/openapi3";

using TypeSpec.Http;
using TypeSpec.Rest;

@service(#{
  title: "FOMO API Service",
})
namespace Fomo;

@doc("A real-time event discovery object")
model Event {
  @doc("Unique identifier")
  @key id: string;
  @doc("Event title")
  title: string;
  @doc("Detailed description")
  description: string;
  @doc("UTC start time")
  timestamp: utcDateTime;
  @doc("Latitude")
  lat: float64;
  @doc("Longitude")
  lng: float64;
}

@route("/events")
interface Events {
  @get list(): Event[];
  @get read(@path id: string): Event | Error;
}

@doc("Standard error response")
model Error {
  code: int32;
  message: string;
}
