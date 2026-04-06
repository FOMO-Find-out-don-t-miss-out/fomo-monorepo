from unittest.mock import patch

import httpx
import pytest
from app.services.harvester.providers.more_com import MoreComProvider
from app.services.harvester.utils.proxy_manager import get_proxy_config


def test_get_proxy_config_no_proxy():
    with patch("app.services.harvester.utils.proxy_manager.settings") as mock_settings:
        mock_settings.SCRAPER_PROXY_URL = None
        config = get_proxy_config()
        assert config is None


def test_get_proxy_config_with_proxy():
    proxy_url = "http://user:pass@proxy.server:8080"
    with patch("app.services.harvester.utils.proxy_manager.settings") as mock_settings:
        mock_settings.SCRAPER_PROXY_URL = proxy_url
        config = get_proxy_config()
        assert config == {
            "http://": proxy_url,
            "https://": proxy_url,
        }


@pytest.mark.asyncio
async def test_more_com_provider_client_no_proxy():
    with patch("app.services.harvester.providers.more_com.get_proxy_config", return_value=None):
        provider = MoreComProvider()
        client = provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        # Check that no proxy mounts are set (other than default)
        for _pattern, transport in client._mounts.items():
            # In httpx, if no proxy is set, it uses AsyncHTTPTransport without proxy
            if isinstance(transport, httpx.AsyncHTTPTransport):
                assert transport._proxy is None
        await client.aclose()


@pytest.mark.asyncio
async def test_more_com_provider_client_with_proxy():
    proxy_url = "http://proxy.server:8080"
    proxy_config = {"http://": proxy_url, "https://": proxy_url}

    patch_path = "app.services.harvester.providers.more_com.get_proxy_config"
    with patch(patch_path, return_value=proxy_config):
        provider = MoreComProvider()
        client = provider._get_client()
        assert isinstance(client, httpx.AsyncClient)

        found_http = False
        found_https = False
        for pattern, transport in client._mounts.items():
            if pattern.pattern == "http://":
                assert isinstance(transport, httpx.AsyncHTTPTransport)
                proxy_val = getattr(transport._pool, "_proxy_url", None)
                assert proxy_val is not None
                # Check attributes of httpcore.URL
                assert proxy_val.scheme == b"http"
                assert proxy_val.host == b"proxy.server"
                assert proxy_val.port == 8080
                found_http = True
            if pattern.pattern == "https://":
                assert isinstance(transport, httpx.AsyncHTTPTransport)
                proxy_val = getattr(transport._pool, "_proxy_url", None)
                assert proxy_val is not None
                assert proxy_val.scheme == b"http"
                assert proxy_val.host == b"proxy.server"
                assert proxy_val.port == 8080
                found_https = True

        assert found_http
        assert found_https
        await client.aclose()


def test_more_com_provider_ensure_string():
    provider = MoreComProvider()
    assert provider._ensure_string(None) is None
    assert provider._ensure_string("test") == "test"
    assert provider._ensure_string(["item1", "item2"]) == "item1"
    assert provider._ensure_string([]) is None
    assert provider._ensure_string([None]) is None


def test_more_com_provider_get_country_code():
    provider = MoreComProvider()
    # Mock registry
    provider.registry = {"example.gr": {"country_code": "GR"}}
    assert provider._get_country_code("https://www.example.gr/path") == "GR"
    assert provider._get_country_code("https://www.something.uk/path") == "GB"
    assert provider._get_country_code("https://www.unknown.xyz/path") == "US"


def test_more_com_provider_normalize_url():
    provider = MoreComProvider()
    base = "https://www.more.com"
    assert provider._normalize_url(None, base) is None
    assert provider._normalize_url("http://test.com", base) == "http://test.com"
    assert provider._normalize_url("//test.com", base) == "https://test.com"
    assert provider._normalize_url("/path", base) == "https://www.more.com/path"
    assert provider._normalize_url("more.com/test", base) == "https://more.com/test"
    assert provider._normalize_url("relative/path", base) == "relative/path"
