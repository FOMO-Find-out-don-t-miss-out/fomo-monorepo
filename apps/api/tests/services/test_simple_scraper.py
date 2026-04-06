from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.harvester.providers.more_com import MoreComProvider
from bs4 import BeautifulSoup


@pytest.mark.asyncio
async def test_more_com_provider_schema_org_success() -> None:
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
    provider = MoreComProvider()
    soup = BeautifulSoup(html, "html.parser")
    result = await provider._extract_schema_org(soup)

    assert result is not None
    assert result["source"] == "schema_org"
    assert result["photo_url"] is None  # Requirement: Stop collecting
    assert result["structured_data"]["name"] == "Test Event"


@pytest.mark.asyncio
async def test_more_com_provider_registry_success() -> None:
    html = """
    <html>
        <h1>Scraped Title</h1>
        <div class="event-description">Description</div>
        <div class="venue-name">Test Venue</div>
        <time itemprop="startDate" datetime="2026-06-01">June 1st</time>
        <img class="event-image" src="/path/to/img.png">
    </html>
    """
    provider = MoreComProvider()
    # The provider loads its own registry.json, which contains more.com selectors.
    # We'll use more.com URL to trigger registry hit.
    soup = BeautifulSoup(html, "html.parser")
    result = await provider._extract_registry(soup, "https://www.more.com/event")

    assert result is not None
    assert result["source"] == "registry"
    assert result["extracted_fields"]["title"] == "Scraped Title"
    assert result["extracted_fields"]["start_time"] == "2026-06-01"
    assert result["extracted_fields"]["image"] == "/path/to/img.png"


def test_provider_factory_get_provider() -> None:
    from app.services.harvester.factory import ProviderFactory

    factory = ProviderFactory()
    # more.com domain
    provider = factory.get_provider("https://www.more.com/event")
    assert isinstance(provider, MoreComProvider)
    # Unknown domain
    provider = factory.get_provider("https://unknown.com/event")
    assert isinstance(provider, MoreComProvider)


@pytest.mark.asyncio
async def test_more_com_provider_fetch_event_registry_hit() -> None:
    provider = MoreComProvider()
    html = "<html><body><h1>Registry Title</h1></body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await provider.fetch_event("https://more.com/event")

        assert result is not None
        assert result.title == "Registry Title"
        assert result.ingestion_method == "registry"


@pytest.mark.asyncio
async def test_more_com_provider_fetch_event_schema_hit() -> None:
    provider = MoreComProvider()
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
        result = await provider.fetch_event("https://other.com/event")

        assert result is not None
        assert result.title == "Schema Title"
        assert result.ingestion_method == "json_ld"


@pytest.mark.asyncio
async def test_more_com_provider_fetch_event_llm_fallback() -> None:
    provider = MoreComProvider()
    html = "<html><body><main>This is the main content of the event.</main></body></html>"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await provider.fetch_event("https://fallback.com/event")

        assert result is not None
        assert result.ingestion_method == "html_fallback"
        assert "main content" in result.raw_text


@pytest.mark.asyncio
async def test_more_com_provider_schema_org_invalid_json() -> None:
    html = '<html><script type="application/ld+json">{invalid}</script></html>'
    soup = BeautifulSoup(html, "html.parser")
    provider = MoreComProvider()
    assert await provider._extract_schema_org(soup) is None


@pytest.mark.asyncio
async def test_more_com_provider_registry_special_elements() -> None:
    provider = MoreComProvider()
    # Mock registry for this test
    provider.registry = {"test.com": {"selectors": {"time": "time", "img": "img", "text": "p"}}}
    html = '<html><time datetime="2026">Day</time><img src="pic.jpg"><p>Hello</p></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = await provider._extract_registry(soup, "http://test.com")
    assert result["extracted_fields"]["time"] == "2026"
    assert result["extracted_fields"]["img"] == "pic.jpg"
    assert result["extracted_fields"]["text"] == "Hello"


@pytest.mark.asyncio
async def test_more_com_provider_discover_links() -> None:
    provider = MoreComProvider()
    html = """
    <html>
        <a href="/tickets/music/event1">Event 1</a>
        <a href="https://www.more.com/tickets/theater/event2">Event 2</a>
        <a href="/offers/some-offer">Offer (Excluded)</a>
        <a href="/gr-el/tickets/">Listing (Excluded)</a>
    </html>
    """
    mock_resp = MagicMock(status_code=200, text=html)

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        links = await provider.discover_links("https://www.more.com/gr-el/tickets/music/")
        assert len(links) == 2
        assert any("event1" in link for link in links)
        assert any("event2" in link for link in links)
        assert all("offers" not in link for link in links)


@pytest.mark.asyncio
async def test_run_scraper_logic() -> None:
    from app.services.harvester.scraper import run_scraper

    # Mock discover_links and fetch_event
    provider_path = "app.services.harvester.providers.more_com.MoreComProvider"
    with patch(f"{provider_path}.discover_links", new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = ["https://more.com/tickets/e1"]

        with patch(f"{provider_path}.fetch_event", new_callable=AsyncMock) as mock_fetch:
            from app.services.harvester.providers.base import ScrapedEvent

            mock_fetch.return_value = ScrapedEvent(
                title="E1",
                original_link="https://more.com/tickets/e1",
                country_code="GR",
                source="registry",
            )

            # We need to mock sys.stdout to avoid printing to console
            with patch("sys.stdout", MagicMock()):
                await run_scraper("https://more.com/list", limit=10)

    assert mock_disc.called
    assert mock_fetch.called


def test_scraper_cli_parsing() -> None:
    from app.services.harvester.scraper import main as scraper_main

    with patch("sys.argv", ["scraper.py", "https://test.com", "--limit", "5"]):
        with patch("asyncio.run") as mock_run:
            scraper_main()
            assert mock_run.called


@pytest.mark.asyncio
async def test_more_com_provider_fetch_event_exception() -> None:
    provider = MoreComProvider()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Network Error")):
        result = await provider.fetch_event("https://error.com")
        assert result is None


@pytest.mark.asyncio
async def test_more_com_provider_schema_org_no_scripts() -> None:
    soup = BeautifulSoup("<html></html>", "html.parser")
    provider = MoreComProvider()
    assert await provider._extract_schema_org(soup) is None


@pytest.mark.asyncio
async def test_more_com_provider_schema_org_not_dict() -> None:
    html = '<html><script type="application/ld+json">"just a string"</script></html>'
    soup = BeautifulSoup(html, "html.parser")
    provider = MoreComProvider()
    assert await provider._extract_schema_org(soup) is None


@pytest.mark.asyncio
async def test_more_com_provider_registry_no_results() -> None:
    provider = MoreComProvider()
    provider.registry = {"test.com": {"selectors": {"title": "nonexistent"}}}
    soup = BeautifulSoup("<html></html>", "html.parser")
    assert await provider._extract_registry(soup, "http://test.com") is None


@pytest.mark.asyncio
async def test_more_com_provider_fetch_event_schema_list() -> None:
    provider = MoreComProvider()
    html = (
        '<html><script type="application/ld+json">'
        '[{"@type": "Event", "name": "E1", "startDate": "2026"}]</script></html>'
    )
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await provider.fetch_event("http://test.com")
        assert result.title == "E1"
