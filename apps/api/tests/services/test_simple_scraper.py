from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.harvester.simple_scraper import (
    RegistryExtractor,
    SchemaOrgExtractor,
    ScraperEngine,
)
from bs4 import BeautifulSoup


@pytest.mark.asyncio
async def test_schema_org_extractor_success() -> None:
    html = """
    <html>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Test Event",
            "startDate": "2026-05-01T20:00:00Z",
            "location": {
                "@type": "Place",
                "name": "Test Venue"
            },
            "image": "https://example.com/image.jpg"
        }
        </script>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    extractor = SchemaOrgExtractor()
    result = await extractor.extract(soup, "https://example.com/event")

    assert result is not None
    assert result["source"] == "schema_org"
    assert result["photo_url"] == "https://example.com/image.jpg"
    assert result["structured_data"]["name"] == "Test Event"


@pytest.mark.asyncio
async def test_schema_org_extractor_list() -> None:
    html = """
    <html>
        <script type="application/ld+json">
        [
            {
                "@type": "Event",
                "name": "Event 1"
            }
        ]
        </script>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    extractor = SchemaOrgExtractor()
    result = await extractor.extract(soup, "https://example.com/event")
    assert result is not None
    assert result["structured_data"]["name"] == "Event 1"


@pytest.mark.asyncio
async def test_registry_extractor_success() -> None:
    registry = {
        "example.com": {
            "selectors": {"title": "h1.title", "start_time": "time.date", "image": "img.poster"}
        }
    }
    html = """
    <html>
        <h1 class="title">Scraped Title</h1>
        <time class="date" datetime="2026-06-01">June 1st</time>
        <img class="poster" src="/path/to/img.png">
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    extractor = RegistryExtractor(registry)
    result = await extractor.extract(soup, "https://www.example.com/event")

    assert result is not None
    assert result["source"] == "registry"
    assert result["extracted_fields"]["title"] == "Scraped Title"
    assert result["extracted_fields"]["start_time"] == "2026-06-01"
    assert result["extracted_fields"]["image"] == "/path/to/img.png"


def test_scraper_engine_get_country_code() -> None:
    engine = ScraperEngine()
    # From registry
    engine.registry = {"example.gr": {"country_code": "GR"}}
    assert engine._get_country_code("https://example.gr/event") == "GR"
    # From TLD
    assert engine._get_country_code("https://something.de/event") == "DE"
    # Default
    assert engine._get_country_code("https://unknown.xyz/event") == "US"


@pytest.mark.asyncio
async def test_scraper_engine_scrape_registry_hit() -> None:
    engine = ScraperEngine()
    registry = {"example.com": {"selectors": {"title": "h1"}}}
    engine.registry = registry
    engine.registry_extractor.registry = registry

    html = "<html><body><h1>Registry Title</h1></body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await engine.scrape("https://example.com/event")

        assert result is not None
        assert result.title == "Registry Title"
        assert result.source == "registry"


@pytest.mark.asyncio
async def test_scraper_engine_scrape_schema_hit() -> None:
    engine = ScraperEngine()
    html = """
    <html>
        <script type="application/ld+json">
        {"@type": "Event", "name": "Schema Title", "startDate": "2026-01-01"}
        </script>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await engine.scrape("https://other.com/event")

        assert result is not None
        assert result.title == "Schema Title"
        assert result.source == "schema_org"


@pytest.mark.asyncio
async def test_scraper_engine_scrape_llm_fallback() -> None:
    engine = ScraperEngine()
    html = "<html><body><main>This is the main content of the event.</main></body></html>"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await engine.scrape("https://fallback.com/event")

        assert result is not None
        assert result.source == "llm_fallback"
        assert "main content" in result.raw_text


@pytest.mark.asyncio
async def test_base_extractor_not_implemented() -> None:
    from app.services.harvester.simple_scraper import BaseExtractor

    extractor = BaseExtractor()
    with pytest.raises(NotImplementedError):
        await extractor.extract(BeautifulSoup("", "html.parser"), "http://test")


@pytest.mark.asyncio
async def test_schema_org_extractor_invalid_json() -> None:
    html = '<html><script type="application/ld+json">{invalid}</script></html>'
    soup = BeautifulSoup(html, "html.parser")
    extractor = SchemaOrgExtractor()
    assert await extractor.extract(soup, "http://test") is None


@pytest.mark.asyncio
async def test_registry_extractor_special_elements() -> None:
    registry = {"test.com": {"selectors": {"time": "time", "img": "img", "text": "p"}}}
    html = '<html><time datetime="2026">Day</time><img src="pic.jpg"><p>Hello</p></html>'
    soup = BeautifulSoup(html, "html.parser")
    extractor = RegistryExtractor(registry)
    result = await extractor.extract(soup, "http://test.com")
    assert result["extracted_fields"]["time"] == "2026"
    assert result["extracted_fields"]["img"] == "pic.jpg"
    assert result["extracted_fields"]["text"] == "Hello"


def test_scraper_engine_load_registry_fail() -> None:
    # Test loading non-existent registry with absolute path
    import os

    abs_path = "C:/non_existent_registry.json" if os.name == "nt" else "/non_existent_registry.json"
    engine = ScraperEngine(registry_path=abs_path)
    assert engine.registry == {}


@pytest.mark.asyncio
async def test_scraper_main_logic() -> None:
    from app.services.harvester.simple_scraper import main as scraper_main

    # Mocking httpx.AsyncClient.get for the listing page and individual scrapes
    mock_resp_listing = MagicMock()
    mock_resp_listing.status_code = 200
    mock_resp_listing.text = '<html><a href="/tickets/event1">Event 1</a></html>'

    mock_resp_event = MagicMock()
    mock_resp_event.status_code = 200
    mock_resp_event.text = (
        '<html><script type="application/ld+json">{"@type": "Event", "name": "E1"}</script></html>'
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_resp_listing, mock_resp_event]
        # We need to mock sys.stdout to avoid printing to console
        with patch("sys.stdout", MagicMock()):
            # Since we cannot easily limit MAX_EVENTS inside main(),
            # we rely on our mock_get.side_effect to handle calls.
            # It will eventually raise StopIteration if more than 2 calls are made.
            try:
                await scraper_main()
            except StopIteration:
                pass

        assert mock_get.call_count >= 1


@pytest.mark.asyncio
async def test_scraper_engine_scrape_exception() -> None:
    engine = ScraperEngine()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Network Error")):
        result = await engine.scrape("https://error.com")
        assert result is None


@pytest.mark.asyncio
async def test_scraper_engine_normalize_url_variations() -> None:
    engine = ScraperEngine()
    # To test _normalize_url, I need to call scrape or mock internal parts.
    # I'll test it via RegistryExtractor image src normalization if possible.
    registry = {"test.com": {"selectors": {"image": "img"}}}
    engine.registry_extractor.registry = registry

    html = '<html><img src="/relative.jpg"></html>'
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await engine.scrape("https://test.com/event")
        assert result.photo_url == "https://test.com/relative.jpg"


@pytest.mark.asyncio
async def test_scraper_engine_ensure_string_list() -> None:
    engine = ScraperEngine()
    # Testing internal helper _ensure_string indirectly via schema extractor if possible,
    # or just testing the engine method directly if accessible.
    # It's a local function inside scrape(), so I'll test it via schema hit.
    html = (
        '<html><script type="application/ld+json">{"@type": "Event", '
        '"name": ["List Title"], "startDate": "2026"}</script></html>'
    )
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await engine.scrape("http://test.com")
        assert result.title == "List Title"


@pytest.mark.asyncio
async def test_scraper_engine_normalize_more_com() -> None:
    engine = ScraperEngine()
    registry = {"more.com": {"selectors": {"image": "img"}}}
    engine.registry_extractor.registry = registry
    html = '<html><img src="more.com/img.jpg"></html>'
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await engine.scrape("https://more.com/event")
        assert result.photo_url == "https://more.com/img.jpg"


@pytest.mark.asyncio
async def test_schema_org_extractor_no_scripts() -> None:
    soup = BeautifulSoup("<html></html>", "html.parser")
    extractor = SchemaOrgExtractor()
    assert await extractor.extract(soup, "http://test") is None


@pytest.mark.asyncio
async def test_schema_org_extractor_not_dict() -> None:
    html = '<html><script type="application/ld+json">"just a string"</script></html>'
    soup = BeautifulSoup(html, "html.parser")
    extractor = SchemaOrgExtractor()
    assert await extractor.extract(soup, "http://test") is None


@pytest.mark.asyncio
async def test_registry_extractor_no_results() -> None:
    registry = {"test.com": {"selectors": {"title": "nonexistent"}}}
    soup = BeautifulSoup("<html></html>", "html.parser")
    extractor = RegistryExtractor(registry)
    assert await extractor.extract(soup, "http://test.com") is None


@pytest.mark.asyncio
async def test_scraper_engine_scrape_no_url() -> None:
    engine = ScraperEngine()
    assert await engine.scrape(None) is None


@pytest.mark.asyncio
async def test_scraper_engine_scrape_schema_list() -> None:
    engine = ScraperEngine()
    html = (
        '<html><script type="application/ld+json">'
        '[{"@type": "Event", "name": "E1", "startDate": "2026"}]</script></html>'
    )
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await engine.scrape("http://test.com")
        assert result.title == "E1"


def test_scraper_engine_load_registry_none() -> None:
    engine = ScraperEngine(registry_path=None)
    assert engine.registry != {}  # Should load default
