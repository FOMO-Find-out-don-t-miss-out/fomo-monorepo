import logging
from typing import Any

from packages.domain.schemas.extracted_event import ExtractedEvent

logger = logging.getLogger(__name__)


class JsonLdExtractor:
    """
    Specialized extractor for JSON-LD / Schema.org event data.
    Focuses on structural parsing only.
    """

    @staticmethod
    def extract(
        data: dict[str, Any] | list[dict[str, Any]],
        source_domain: str | None = None,
    ) -> list[ExtractedEvent]:
        """
        Maps Schema.org / JSON-LD event data to ExtractedEvent objects.
        Returns a list of events (handles single and multi-day/event formats).
        """
        try:
            if isinstance(data, list):
                items = data
            else:
                items = [data]

            extracted_events = []
            for item_data in items:
                # Basic validation that this is an Event
                item_type_raw = item_data.get("@type", "")
                item_types = (
                    item_type_raw if isinstance(item_type_raw, list) else [str(item_type_raw)]
                )
                if not any(
                    "Event" in t or t in ["Event", "MusicEvent", "Festival"] for t in item_types
                ):
                    continue

                def get_val(key: str, data: dict[str, Any] = item_data) -> object | None:
                    val = data.get(key)
                    return val[0] if isinstance(val, list) else val

                title = get_val("name") or get_val("headline")
                if not title:
                    continue

                location = item_data.get("location", {})
                location_name = None
                lat = None
                lng = None
                street_address = None

                if isinstance(location, list) and location:
                    location = location[0]

                if isinstance(location, dict):
                    location_name = location.get("name")
                    geo = location.get("geo", {})
                    if isinstance(geo, dict):
                        lat_raw = geo.get("latitude")
                        lng_raw = geo.get("longitude")
                        try:
                            lat_val = lat_raw[0] if isinstance(lat_raw, list) else lat_raw
                            lng_val = lng_raw[0] if isinstance(lng_raw, list) else lng_raw
                            lat = float(lat_val) if lat_val is not None else None
                            lng = float(lng_val) if lng_val is not None else None
                        except (ValueError, TypeError):
                            lat = None
                            lng = None

                    address_data = location.get("address")
                    if isinstance(address_data, dict):
                        street_address = address_data.get("streetAddress")
                    elif isinstance(address_data, str):
                        street_address = address_data
                elif isinstance(location, str):
                    location_name = location
                    street_address = location

                # Extract image
                photo_url = None
                image_data = item_data.get("image")
                if isinstance(image_data, str):
                    photo_url = image_data
                elif isinstance(image_data, list) and len(image_data) > 0:
                    first_img = image_data[0]
                    photo_url = first_img if isinstance(first_img, str) else first_img.get("url")
                elif isinstance(image_data, dict):
                    photo_url = image_data.get("url")

                # Prepare common fields
                common_fields = {
                    "title": str(title),
                    "location_name": location_name,
                    "street_address": street_address,
                    "lat": lat,
                    "lng": lng,
                    "ticket_url": str(get_val("url")) if get_val("url") else None,
                    "description": str(get_val("description")) if get_val("description") else None,
                    "source_provider": source_domain or "unknown",
                    "ingestion_method": "json_ld",
                }

                # Multi-Day Support
                start_dates = item_data.get("startDate")
                end_dates = item_data.get("endDate")

                if isinstance(start_dates, list) and len(start_dates) > 1:
                    for i, start_date in enumerate(start_dates):
                        end_date = None
                        if isinstance(end_dates, list) and len(end_dates) > i:
                            end_date = end_dates[i]

                        event_metadata = {**item_data, "source_domain": source_domain}
                        if photo_url:
                            event_metadata["image"] = photo_url

                        extracted_events.append(
                            ExtractedEvent(
                                **common_fields,
                                start_time=start_date,  # type: ignore
                                end_time=end_date,  # type: ignore
                                event_metadata=event_metadata,
                            )
                        )
                else:
                    event_metadata = {**item_data, "source_domain": source_domain}
                    if photo_url:
                        event_metadata["image"] = photo_url

                    extracted_events.append(
                        ExtractedEvent(
                            **common_fields,
                            start_time=item_data.get("startDate"),  # type: ignore
                            end_time=item_data.get("endDate"),  # type: ignore
                            event_metadata=event_metadata,
                        )
                    )

            return extracted_events
        except Exception as e:
            logger.error(f"Error extracting JSON-LD: {e}")
            return []
