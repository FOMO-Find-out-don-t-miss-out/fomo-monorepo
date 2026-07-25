import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import (
    Event,
    EventCategory,
    EventProvenance,
    EventStatus,
    EventVisibility,
    Organizer,
)

# All fixture dates are relative to "now" at collection time rather than
# hardcoded years, so the always-on upcoming-only filter (see events.py
# search_events) never accidentally treats a fixture as already-ended.
NOW = datetime.now(UTC)
FUTURE = NOW + timedelta(days=30)
LATER_FUTURE = NOW + timedelta(days=31)
PAST = NOW - timedelta(days=30)

ATHENS_LAT, ATHENS_LNG = 37.9838, 23.7275
PIRAEUS_LAT, PIRAEUS_LNG = 37.9422, 23.6462  # ~7km from Athens
THESSALONIKI_LAT, THESSALONIKI_LNG = 40.6401, 22.9444  # ~300km from Athens

SEARCH_URL = "/api/v1/events/search"


# --- Fixture helpers ---------------------------------------------------------


def _make_event(
    *,
    title: str,
    start_time: datetime = FUTURE,
    end_time: datetime | None = None,
    category: str = EventCategory.Music.value,
    location_name: str | None = "Test Venue",
    organizer_id: UUID | None = None,
    status: EventStatus = EventStatus.live,
    visibility: EventVisibility = EventVisibility.public,
    provenance: EventProvenance = EventProvenance.aggregated,
    location: str = "POINT(23.7275 37.9838)",
    removed_at: datetime | None = None,
) -> Event:
    return Event(
        title=title,
        location=location,
        start_time=start_time,
        end_time=end_time,
        category=category,
        location_name=location_name,
        organizer_id=organizer_id,
        source_url="http://example.com",
        status=status,
        visibility=visibility,
        provenance=provenance,
        removed_at=removed_at,
    )


def _register_sqlite_spatial_functions(session: Session) -> None:
    """Mirror the spatial-function shims registered in test_discovery.py, so
    location-based /events/search tests can run against the SQLite-backed
    test database used across this suite.
    """

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def sqlite_st_dwithin(loc: str, pnt: str, radius_m: float) -> int:
        try:
            l_parts = loc.replace("POINT(", "").replace(")", "").split()
            p_parts = pnt.replace("POINT(", "").replace(")", "").split()
            lng1, lat1 = float(l_parts[0]), float(l_parts[1])
            lng2, lat2 = float(p_parts[0]), float(p_parts[1])
            return 1 if (haversine(lat1, lng1, lat2, lng2) * 1000) <= radius_m else 0
        except Exception:
            return 0

    def sqlite_st_distance(loc: str, pnt: str) -> float:
        try:
            l_parts = loc.replace("POINT(", "").replace(")", "").split()
            p_parts = pnt.replace("POINT(", "").replace(")", "").split()
            lng1, lat1 = float(l_parts[0]), float(l_parts[1])
            lng2, lat2 = float(p_parts[0]), float(p_parts[1])
            return haversine(lat1, lng1, lat2, lng2) * 1000
        except Exception:
            return 0.0

    conn = session.connection().connection
    try:
        conn.create_function("ST_DWithin", 3, sqlite_st_dwithin)
        conn.create_function("ST_Distance", 2, sqlite_st_distance)
        conn.create_function("ST_SetSRID", 2, lambda x, s: x)
        conn.create_function("ST_MakePoint", 2, lambda x, y: f"POINT({x} {y})")
    except AttributeError:
        pass


# --- 1. Route reachability / ordering ----------------------------------------


@pytest.mark.asyncio
async def test_search_route_is_reachable_and_not_captured_by_event_id_route(
    client: AsyncClient,
) -> None:
    """If /search were registered after /{event_id}, "search" would be
    parsed as an event_id path param instead of hitting this handler.
    """
    response = await client.get(SEARCH_URL, params={"q": "anything"})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"results", "limit", "offset", "has_more"}
    assert body["results"] == []


# --- 2-4. Criteria / normalization rejection ---------------------------------


@pytest.mark.asyncio
async def test_no_criteria_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_whitespace_only_q_with_no_other_criterion_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.get(SEARCH_URL, params={"q": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_one_character_normalized_q_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"q": "a"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_one_character_after_trimming_returns_422(client: AsyncClient) -> None:
    """"  a  " strips to "a" (length 1) — must still 422, proving strip
    happens before the minimum-length check rather than after.
    """
    response = await client.get(SEARCH_URL, params={"q": "  a  "})
    assert response.status_code == 422


# --- 5. Whitespace normalization on a valid query ----------------------------


@pytest.mark.asyncio
async def test_leading_and_trailing_whitespace_is_normalized(
    client: AsyncClient, session: Session
) -> None:
    session.add(_make_event(title="Jazz Night"))
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "  Jazz  "})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Jazz Night" in titles


# --- 6. Literal wildcard characters are not treated as SQL wildcards ---------


@pytest.mark.asyncio
async def test_literal_percent_sign_is_not_treated_as_wildcard(
    client: AsyncClient, session: Session
) -> None:
    # If '%' in the user query were left unescaped, the resulting pattern
    # "%A%B%" would match "AxyzB" even though "A%B" never literally occurs.
    decoy = _make_event(title="AxyzB Unrelated Show")
    session.add(decoy)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "A%B"})
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.asyncio
async def test_literal_underscore_is_not_treated_as_wildcard(
    client: AsyncClient, session: Session
) -> None:
    # If '_' were left unescaped, it means "exactly one character" in LIKE,
    # so the pattern "%A_B%" would match "AxB" even though "A_B" never
    # literally occurs.
    decoy = _make_event(title="AxB Unrelated Show")
    session.add(decoy)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "A_B"})
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.asyncio
async def test_literal_percent_and_underscore_do_match_when_actually_present(
    client: AsyncClient, session: Session
) -> None:
    event = _make_event(title="Save 100%_off Tonight")
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "100%_off"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Save 100%_off Tonight" in titles


# --- 7. Basic substring search ------------------------------------------------


@pytest.mark.asyncio
async def test_title_substring_search(client: AsyncClient, session: Session) -> None:
    session.add(_make_event(title="Big Jazz Bash"))
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "azz"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Big Jazz Bash" in titles


# --- 8-9. Match-priority ordering: exact > prefix > substring ---------------


@pytest.mark.asyncio
async def test_exact_then_prefix_then_substring_title_ordering(
    client: AsyncClient, session: Session
) -> None:
    exact = _make_event(title="Jazz", start_time=FUTURE)
    prefix = _make_event(title="Jazz Fusion Night", start_time=FUTURE)
    substring = _make_event(title="Big Jazz Bash", start_time=FUTURE)
    # Insertion order deliberately not priority order, to prove sorting.
    session.add_all([substring, exact, prefix])
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Jazz"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert titles == ["Jazz", "Jazz Fusion Night", "Big Jazz Bash"]


# --- 10. Title matches rank before location_name matches ---------------------


@pytest.mark.asyncio
async def test_title_match_ranks_before_location_name_match(
    client: AsyncClient, session: Session
) -> None:
    title_match = _make_event(
        title="Blues Fest", location_name="Riverside Arena", start_time=FUTURE
    )
    venue_match = _make_event(
        title="Autumn Gathering", location_name="Blues Alley Club", start_time=FUTURE
    )
    session.add_all([venue_match, title_match])
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Blues"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert titles == ["Blues Fest", "Autumn Gathering"]


# --- 11. Location_name matches rank before organizer-name matches -----------


@pytest.mark.asyncio
async def test_location_name_match_ranks_before_organizer_match(
    client: AsyncClient, session: Session
) -> None:
    organizer = Organizer(display_name="Rockstar Presents")
    session.add(organizer)
    session.commit()

    venue_match = _make_event(
        title="Autumn Gathering", location_name="Rock Hall", start_time=FUTURE
    )
    organizer_match = _make_event(
        title="Spring Session",
        location_name="Test Venue",
        organizer_id=organizer.id,
        start_time=FUTURE,
    )
    session.add_all([organizer_match, venue_match])
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Rock"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert titles == ["Autumn Gathering", "Spring Session"]


# --- 12. Organizer-name-only search works ------------------------------------


@pytest.mark.asyncio
async def test_organizer_name_search_works(client: AsyncClient, session: Session) -> None:
    organizer = Organizer(display_name="Stellar Presents")
    session.add(organizer)
    session.commit()

    event = _make_event(
        title="Midnight Session", location_name="Test Venue", organizer_id=organizer.id
    )
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Stellar"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Midnight Session" in titles


# --- 13. Missing organizer / location_name never crash the query ------------


@pytest.mark.asyncio
async def test_missing_organizer_and_location_name_does_not_fail(
    client: AsyncClient, session: Session
) -> None:
    event = _make_event(title="Nebula Nights", location_name=None, organizer_id=None)
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Nebula"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Nebula Nights" in titles


# --- 14-16. Category filtering -----------------------------------------------


@pytest.mark.asyncio
async def test_category_filter_accepts_valid_enum_value(
    client: AsyncClient, session: Session
) -> None:
    music = _make_event(title="Music Show", category=EventCategory.Music.value)
    sports = _make_event(title="Sports Match", category=EventCategory.Sports.value)
    session.add_all([music, sports])
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Music"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert titles == ["Music Show"]


@pytest.mark.asyncio
async def test_invalid_category_value_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"category": "NotARealCategory"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_multiple_categories_use_in_semantics(
    client: AsyncClient, session: Session
) -> None:
    music = _make_event(title="Music Show", category=EventCategory.Music.value)
    sports = _make_event(title="Sports Match", category=EventCategory.Sports.value)
    food = _make_event(title="Food Fair", category=EventCategory.Food.value)
    session.add_all([music, sports, food])
    session.commit()

    response = await client.get(
        SEARCH_URL, params={"category": ["Music", "Sports"]}
    )
    assert response.status_code == 200
    titles = {e["title"] for e in response.json()["results"]}
    assert titles == {"Music Show", "Sports Match"}


# --- 17-19. Location pairing validation --------------------------------------


@pytest.mark.asyncio
async def test_lat_without_lng_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"lat": ATHENS_LAT})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lng_without_lat_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"lng": ATHENS_LNG})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_radius_without_lat_lng_returns_422(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"radius_km": 5})
    assert response.status_code == 422


# --- 20. Default radius is 10km when omitted --------------------------------


@pytest.mark.asyncio
async def test_lat_lng_without_radius_uses_default_10km(
    client: AsyncClient, session: Session
) -> None:
    _register_sqlite_spatial_functions(session)

    nearby = _make_event(
        title="Athens Event",
        location=f"POINT({ATHENS_LNG} {ATHENS_LAT})",
    )
    far = _make_event(
        title="Thessaloniki Event",
        location=f"POINT({THESSALONIKI_LNG} {THESSALONIKI_LAT})",
    )
    session.add_all([nearby, far])
    session.commit()

    response = await client.get(
        SEARCH_URL, params={"lat": ATHENS_LAT, "lng": ATHENS_LNG}
    )
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Athens Event" in titles
    assert "Thessaloniki Event" not in titles


# --- 21. Radius bounds --------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("radius_km", [0, -1, 201, 500])
async def test_radius_out_of_bounds_returns_422(
    client: AsyncClient, radius_km: float
) -> None:
    response = await client.get(
        SEARCH_URL,
        params={"lat": ATHENS_LAT, "lng": ATHENS_LNG, "radius_km": radius_km},
    )
    assert response.status_code == 422


# --- 22. date_to must be strictly later than date_from -----------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("delta", [timedelta(0), timedelta(hours=-1)])
async def test_date_to_not_later_than_date_from_returns_422(
    client: AsyncClient, delta: timedelta
) -> None:
    date_from = FUTURE
    date_to = date_from + delta
    response = await client.get(
        SEARCH_URL,
        params={
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert response.status_code == 422


# --- 23. Naive datetimes are rejected -----------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["date_from", "date_to"])
async def test_naive_datetime_returns_422(client: AsyncClient, field: str) -> None:
    naive_iso = FUTURE.replace(tzinfo=None).isoformat()
    response = await client.get(SEARCH_URL, params={field: naive_iso})
    assert response.status_code == 422


# --- 24-25. Date-range overlap semantics -------------------------------------


@pytest.mark.asyncio
async def test_event_overlapping_date_from_is_included(
    client: AsyncClient, session: Session
) -> None:
    # Started before date_from, still ongoing (effective end after date_from).
    ongoing = _make_event(
        title="Ongoing Festival",
        start_time=NOW + timedelta(days=1),
        end_time=NOW + timedelta(days=10),
    )
    session.add(ongoing)
    session.commit()

    date_from = NOW + timedelta(days=5)
    response = await client.get(SEARCH_URL, params={"date_from": date_from.isoformat()})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Ongoing Festival" in titles


@pytest.mark.asyncio
async def test_date_to_is_exclusive(client: AsyncClient, session: Session) -> None:
    date_to = NOW + timedelta(days=10)
    on_boundary = _make_event(title="On Boundary", start_time=date_to)
    before_boundary = _make_event(
        title="Before Boundary", start_time=date_to - timedelta(minutes=1)
    )
    session.add_all([on_boundary, before_boundary])
    session.commit()

    response = await client.get(SEARCH_URL, params={"date_to": date_to.isoformat()})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Before Boundary" in titles
    assert "On Boundary" not in titles


# --- 26-27. Upcoming-only behavior (always on, no request parameter) --------


@pytest.mark.asyncio
async def test_already_ended_events_are_excluded(
    client: AsyncClient, session: Session
) -> None:
    ended = _make_event(
        title="Ended Show", start_time=PAST, end_time=PAST + timedelta(hours=2)
    )
    session.add(ended)
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Music"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Ended Show" not in titles


@pytest.mark.asyncio
async def test_live_public_upcoming_event_is_included(
    client: AsyncClient, session: Session
) -> None:
    event = _make_event(title="Upcoming Show", start_time=FUTURE)
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Music"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Upcoming Show" in titles


# --- 28-30. Visibility / lifecycle exclusions --------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "visibility"),
    [
        (EventStatus.removed, EventVisibility.public),
        (EventStatus.live, EventVisibility.hidden),
        (EventStatus.live, EventVisibility.restricted),
        (EventStatus.live, EventVisibility.shadow_hidden),
        (EventStatus.expired, EventVisibility.public),
        (EventStatus.archived, EventVisibility.public),
        (EventStatus.under_investigation, EventVisibility.public),
    ],
)
async def test_non_visible_or_non_live_events_are_excluded(
    client: AsyncClient,
    session: Session,
    status: EventStatus,
    visibility: EventVisibility,
) -> None:
    event = _make_event(
        title="Should Not Appear", status=status, visibility=visibility
    )
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Music"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Should Not Appear" not in titles


# --- 31-33. Filter-only / query-only / query-plus-location combinations -----


@pytest.mark.asyncio
async def test_filter_only_search_works_without_q(
    client: AsyncClient, session: Session
) -> None:
    event = _make_event(title="Category Only Event", category=EventCategory.Art.value)
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Art"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Category Only Event" in titles


@pytest.mark.asyncio
async def test_query_without_location_works(
    client: AsyncClient, session: Session
) -> None:
    event = _make_event(title="Nomad Session")
    session.add(event)
    session.commit()

    response = await client.get(SEARCH_URL, params={"q": "Nomad"})
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert "Nomad Session" in titles


@pytest.mark.asyncio
async def test_query_plus_location_applies_both_conditions(
    client: AsyncClient, session: Session
) -> None:
    _register_sqlite_spatial_functions(session)

    matches_both = _make_event(
        title="Athens Jazz Night",
        location=f"POINT({ATHENS_LNG} {ATHENS_LAT})",
    )
    matches_text_only = _make_event(
        title="Thessaloniki Jazz Night",
        location=f"POINT({THESSALONIKI_LNG} {THESSALONIKI_LAT})",
    )
    matches_location_only = _make_event(
        title="Athens Comedy Show",
        location=f"POINT({ATHENS_LNG} {ATHENS_LAT})",
    )
    session.add_all([matches_both, matches_text_only, matches_location_only])
    session.commit()

    response = await client.get(
        SEARCH_URL,
        params={"q": "Jazz", "lat": ATHENS_LAT, "lng": ATHENS_LNG, "radius_km": 10},
    )
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()["results"]]
    assert titles == ["Athens Jazz Night"]


# --- 34. Pagination: limit / offset / has_more -------------------------------


@pytest.mark.asyncio
async def test_pagination_limit_offset_and_has_more(
    client: AsyncClient, session: Session
) -> None:
    events = [
        _make_event(title=f"Page Event {i}", start_time=FUTURE + timedelta(hours=i))
        for i in range(3)
    ]
    session.add_all(events)
    session.commit()

    first_page = await client.get(
        SEARCH_URL, params={"category": "Music", "limit": 2, "offset": 0}
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["results"]) == 2
    assert first_body["limit"] == 2
    assert first_body["offset"] == 0
    assert first_body["has_more"] is True

    second_page = await client.get(
        SEARCH_URL, params={"category": "Music", "limit": 2, "offset": 2}
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["results"]) == 1
    assert second_body["has_more"] is False


# --- 35-36. Deterministic ordering across requests, id as final tie-breaker -


@pytest.mark.asyncio
async def test_repeated_identical_requests_return_deterministic_ordering(
    client: AsyncClient, session: Session
) -> None:
    events = [
        _make_event(title=f"Tie Event {i}", start_time=FUTURE) for i in range(4)
    ]
    session.add_all(events)
    session.commit()

    first = await client.get(SEARCH_URL, params={"category": "Music"})
    second = await client.get(SEARCH_URL, params={"category": "Music"})
    assert first.status_code == 200
    assert second.status_code == 200

    first_ids = [e["id"] for e in first.json()["results"]]
    second_ids = [e["id"] for e in second.json()["results"]]
    assert first_ids == second_ids


@pytest.mark.asyncio
async def test_event_id_is_the_final_deterministic_tie_breaker(
    client: AsyncClient, session: Session
) -> None:
    # Identical start_time, no q, no location — only `id ASC` can order these.
    events = [
        _make_event(title=f"Same Start Time {i}", start_time=FUTURE) for i in range(4)
    ]
    session.add_all(events)
    session.commit()

    response = await client.get(SEARCH_URL, params={"category": "Music"})
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()["results"]]
    assert ids == sorted(ids)
