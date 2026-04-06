from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.services.harvester.providers.more_com import CircuitBreakerError, MoreComProvider
from app.services.harvester.utils.headers_manager import get_rotated_headers


def test_get_rotated_headers():
    headers = get_rotated_headers()
    assert "User-Agent" in headers
    assert "Accept-Language" in headers
    assert "Sec-Fetch-User" in headers

    # Test randomization
    headers2 = get_rotated_headers()
    # It might be the same by chance but usually different if we call it enough
    # For a simple test, just check they are valid dicts
    assert isinstance(headers2, dict)


@pytest.mark.asyncio
async def test_circuit_breaker_403():
    provider = MoreComProvider()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403

    with pytest.raises(CircuitBreakerError):
        provider._handle_response(mock_response, "http://test.com")


@pytest.mark.asyncio
async def test_circuit_breaker_429():
    provider = MoreComProvider()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429

    with pytest.raises(CircuitBreakerError):
        provider._handle_response(mock_response, "http://test.com")


@pytest.mark.asyncio
async def test_more_com_uses_rotated_headers():
    with patch("app.services.harvester.providers.more_com.get_rotated_headers") as mock_rotate:
        mock_rotate.return_value = {"User-Agent": "RotatedUA"}
        provider = MoreComProvider()
        client = provider._get_client()
        assert client.headers["User-Agent"] == "RotatedUA"
        await client.aclose()


@pytest.mark.asyncio
async def test_discover_links_delays():
    provider = MoreComProvider()
    target_url = "https://www.more.com/tickets/en/"

    with patch("asyncio.sleep") as mock_sleep:
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            mock_get.return_value = mock_response

            await provider.discover_links(target_url)

            # Check that sleep was called
            mock_sleep.assert_called_once()
            args, _ = mock_sleep.call_args
            assert 1.5 <= args[0] <= 4.0


@pytest.mark.asyncio
async def test_fetch_event_delays():
    provider = MoreComProvider()
    event_url = "https://www.more.com/tickets/en/event-1/"

    with patch("asyncio.sleep") as mock_sleep:
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            mock_get.return_value = mock_response

            await provider.fetch_event(event_url)

            # Check that sleep was called
            mock_sleep.assert_called_once()
            args, _ = mock_sleep.call_args
            assert 2.0 <= args[0] <= 5.0
