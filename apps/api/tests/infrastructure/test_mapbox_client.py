import httpx
import pytest
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxResponse


@pytest.mark.asyncio
async def test_search_box_success(respx_mock: object) -> None:
    token = "fake-token"
    client = MapboxClient(access_token=token)
    mock_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "1",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [23.7, 37.9]},
                "properties": {"name": "Athens", "full_address": "Athens, Greece"},
                "relevance": 1.0,
            }
        ],
    }
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    resp = await client.search_box("Athens")
    assert isinstance(resp, MapboxResponse)
    assert len(resp.features) == 1
    assert resp.features[0].properties["name"] == "Athens"


@pytest.mark.asyncio
async def test_geocode_v6_success(respx_mock: object) -> None:
    token = "fake-token"
    client = MapboxClient(access_token=token)
    mock_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "1",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [23.7, 37.9]},
                "properties": {"name": "Athens", "full_address": "Athens, Greece"},
                "relevance": 1.0,
            }
        ],
    }
    respx_mock.get(MapboxClient.GEOCODING_V6_URL).mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    resp = await client.geocode_v6("Athens")
    assert isinstance(resp, MapboxResponse)
    assert len(resp.features) == 1


@pytest.mark.asyncio
async def test_mapbox_422_error(respx_mock: object) -> None:
    token = "fake-token"
    client = MapboxClient(access_token=token)
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(
        return_value=httpx.Response(422, text="Invalid params")
    )

    resp = await client.search_box("Athens")
    assert resp is None


@pytest.mark.asyncio
async def test_mapbox_generic_error(respx_mock: object) -> None:
    token = "fake-token"
    client = MapboxClient(access_token=token)
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(return_value=httpx.Response(500))

    resp = await client.search_box("Athens")
    assert resp is None


@pytest.mark.asyncio
async def test_mapbox_no_token() -> None:
    client = MapboxClient(access_token=None)
    # This should return None immediately because token is missing
    resp = await client.search_box("Athens")
    assert resp is None


@pytest.mark.asyncio
async def test_mapbox_limit(respx_mock: object) -> None:
    token = "fake"
    client = MapboxClient(access_token=token)
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    resp = await client.search_box("Athens", limit=10)
    assert resp is not None
    assert respx_mock.calls.last.request.url.params["limit"] == "10"


@pytest.mark.asyncio
async def test_mapbox_exception(respx_mock: object) -> None:
    token = "fake"
    client = MapboxClient(access_token=token)
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).side_effect = httpx.RequestError("Conn Error")
    resp = await client.search_box("Athens")
    assert resp is None
