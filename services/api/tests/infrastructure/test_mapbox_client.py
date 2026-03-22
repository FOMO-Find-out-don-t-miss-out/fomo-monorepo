import pytest
import httpx
import respx
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxResponse

@pytest.mark.asyncio
async def test_search_box_success(respx_mock):
    client = MapboxClient(access_token="fake-token")
    mock_data = {
        "type": "FeatureCollection",
        "features": [{
            "id": "1", "type": "Feature",
            "geometry": {"coordinates": [23.7, 37.9]},
            "properties": {"name": "Athens"}
        }]
    }
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(return_value=httpx.Response(200, json=mock_data))
    
    resp = await client.search_box("Athens")
    assert resp is not None
    assert len(resp.features) == 1
    assert resp.features[0].properties["name"] == "Athens"

@pytest.mark.asyncio
async def test_geocode_v6_success(respx_mock):
    client = MapboxClient(access_token="fake-token")
    mock_data = {
        "type": "FeatureCollection",
        "features": [{
            "id": "2", "type": "Feature",
            "geometry": {"coordinates": [23.7, 37.9]},
            "properties": {"name": "Thessaloniki"}
        }]
    }
    respx_mock.get(MapboxClient.GEOCODING_V6_URL).mock(return_value=httpx.Response(200, json=mock_data))
    
    resp = await client.geocode_v6("Thessaloniki")
    assert resp is not None
    assert resp.features[0].properties["name"] == "Thessaloniki"

@pytest.mark.asyncio
async def test_mapbox_422_error(respx_mock):
    client = MapboxClient(access_token="fake-token")
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(return_value=httpx.Response(422, text="Invalid params"))
    
    resp = await client.search_box("Invalid")
    assert resp is None

@pytest.mark.asyncio
async def test_mapbox_generic_error(respx_mock):
    client = MapboxClient(access_token="fake-token")
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(return_value=httpx.Response(500))
    
    resp = await client.search_box("Error")
    assert resp is None

@pytest.mark.asyncio
async def test_no_token():
    client = MapboxClient(access_token=None)
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.core.config.settings.MAPBOX_ACCESS_TOKEN", None)
        resp = await client.search_box("Athens")
        assert resp is None

@pytest.mark.asyncio
async def test_mapbox_limit(respx_mock):
    client = MapboxClient(access_token="fake")
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).mock(return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []}))
    await client.search_box("Athens", limit=10)
    assert respx_mock.calls.last.request.url.params["limit"] == "10"

@pytest.mark.asyncio
async def test_mapbox_exception(respx_mock):
    client = MapboxClient(access_token="fake")
    respx_mock.get(MapboxClient.SEARCH_BOX_URL).side_effect = httpx.RequestError("Conn Error")
    resp = await client.search_box("Athens")
    assert resp is None
