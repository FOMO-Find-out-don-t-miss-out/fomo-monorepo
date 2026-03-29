import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class ScrapedEvent(BaseModel):
    title: str | None = None
    description: str | None = None
    location_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    photo_url: str | None = None
    original_link: str
    country_code: str
    source: str
    raw_text: str | None = None
    structured_data: dict[str, Any] | None = None


class BaseExtractor:
    async def extract(self, soup: BeautifulSoup, url: str) -> dict[str, Any] | None:
        raise NotImplementedError


class SchemaOrgExtractor(BaseExtractor):
    """Extracts data using JSON-LD schema.org objects."""

    async def extract(self, soup: BeautifulSoup, url: str) -> dict[str, Any] | None:
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("@type") == "Event" or "Event" in str(item.get("@type", "")):
                        photo_url = None
                        image_data = item.get("image")
                        if isinstance(image_data, str):
                            photo_url = image_data
                        elif isinstance(image_data, list) and len(image_data) > 0:
                            first_img = image_data[0]
                            photo_url = (
                                first_img if isinstance(first_img, str) else first_img.get("url")
                            )
                        elif isinstance(image_data, dict):
                            photo_url = image_data.get("url")

                        return {
                            "structured_data": item,
                            "photo_url": photo_url,
                            "source": "schema_org",
                        }
            except (json.JSONDecodeError, TypeError):
                continue
        return None


class RegistryExtractor(BaseExtractor):
    """Extracts data using site-specific CSS selectors from registry.json."""

    def __init__(self, registry: dict[str, Any]) -> None:
        self.registry = registry

    async def extract(self, soup: BeautifulSoup, url: str) -> dict[str, Any] | None:
        domain = urlparse(url).netloc.replace("www.", "")
        config = self.registry.get(domain)
        if not config or "selectors" not in config:
            return None

        selectors = config["selectors"]
        extracted: dict[str, str] = {}
        for field, selector in selectors.items():
            element = soup.select_one(selector)
            if element:
                if element.name == "time" and element.has_attr("datetime"):
                    extracted[field] = element["datetime"]
                elif element.name == "img" and element.has_attr("src"):
                    extracted[field] = element["src"]
                else:
                    extracted[field] = element.get_text(strip=True)

        if extracted:
            return {"extracted_fields": extracted, "source": "registry"}
        return None


class ScraperEngine:
    def __init__(self, registry_path: str = "app/services/harvester/registry.json") -> None:
        self.registry = self._load_registry(registry_path)
        self.schema_extractor = SchemaOrgExtractor()
        self.registry_extractor = RegistryExtractor(self.registry)
        self.tld_to_country: dict[str, str] = {
            "gr": "GR",
            "uk": "GB",
            "de": "DE",
            "fr": "FR",
            "it": "IT",
            "es": "ES",
            "us": "US",
            "com": "US",
        }

    def _load_registry(self, path_str: str | None) -> dict[str, Any]:
        if path_str:
            path = Path(path_str)
            if not path.is_absolute():
                path = Path(__file__).parent / "registry.json"
        else:
            path = Path(__file__).parent / "registry.json"

        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load registry from {path}: {e}")
            return {}

    def _get_country_code(self, url: str) -> str:
        domain = urlparse(url).netloc.replace("www.", "")
        if domain in self.registry:
            return self.registry[domain].get("country_code", "US")

        tld = domain.split(".")[-1].lower()
        return self.tld_to_country.get(tld, "US")

    async def scrape(self, url: str) -> ScrapedEvent | None:
        def _ensure_string(val: object) -> str | None:
            if val is None:
                return None
            if isinstance(val, list):
                if not val or val[0] is None:
                    return None
                return str(val[0])
            return str(val)

        def _normalize_url(u: str | None, base: str) -> str | None:
            if not u:
                return None
            u = u.strip()
            if u.startswith("http"):
                return u
            if u.startswith("//"):
                return f"https:{u}"
            if u.startswith("/"):
                return f"{base.rstrip('/')}/{u.lstrip('/')}"
            if u.startswith("more.com") or u.startswith("www.more.com"):
                return f"https://{u}"
            return u

        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0
            ) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

                soup = BeautifulSoup(response.text, "html.parser")
                country_code = self._get_country_code(url)
                parsed_url = urlparse(url)
                base_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

                meta_image = None
                og_image = soup.find("meta", property="og:image") or soup.find(
                    "meta", attrs={"name": "og:image"}
                )
                twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
                if og_image:
                    meta_image = og_image.get("content")
                elif twitter_image:
                    meta_image = twitter_image.get("content")

                meta_image = _normalize_url(meta_image, base_origin)

                registry_data = await self.registry_extractor.extract(soup, url)
                if registry_data:
                    fields = registry_data["extracted_fields"]
                    return ScrapedEvent(
                        title=_ensure_string(fields.get("title")),
                        description=_ensure_string(fields.get("description")),
                        location_name=_ensure_string(fields.get("location")),
                        start_time=_ensure_string(fields.get("start_time")),
                        end_time=_ensure_string(fields.get("end_time")),
                        photo_url=_normalize_url(fields.get("image"), base_origin) or meta_image,
                        original_link=url,
                        country_code=country_code,
                        source="registry",
                    )

                schema_data = await self.schema_extractor.extract(soup, url)
                if schema_data:
                    sd = schema_data["structured_data"]
                    loc = sd.get("location")
                    loc_name = None
                    if isinstance(loc, dict):
                        loc_name = loc.get("name")
                    elif isinstance(loc, list) and loc:
                        loc_name = loc[0].get("name") if isinstance(loc[0], dict) else loc[0]
                    else:
                        loc_name = loc

                    return ScrapedEvent(
                        title=_ensure_string(sd.get("name")),
                        description=_ensure_string(sd.get("description")),
                        location_name=_ensure_string(loc_name),
                        start_time=_ensure_string(sd.get("startDate")),
                        end_time=_ensure_string(sd.get("endDate")),
                        photo_url=_normalize_url(schema_data.get("photo_url"), base_origin)
                        or meta_image,
                        original_link=url,
                        country_code=country_code,
                        source="schema_org",
                        structured_data=sd,
                    )

                noise_selectors = ["header", "footer", "nav", "aside", "script", "style"]
                for element in soup.find_all(noise_selectors):
                    element.decompose()

                main_content = soup.find("main") or soup.find("article") or soup.find("body")
                raw_text = ""
                if main_content:
                    raw_text = re.sub(
                        r"\s+", " ", main_content.get_text(separator=" ", strip=True)
                    ).strip()

                return ScrapedEvent(
                    photo_url=meta_image,
                    original_link=url,
                    country_code=country_code,
                    source="llm_fallback",
                    raw_text=raw_text[:5000],
                )

        except Exception as e:
            logger.error(f"ScraperEngine error for {url}: {e}")
            return None


async def main() -> None:
    import sys
    import traceback

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    TARGET_URL = "https://www.more.com/gr-el/tickets/music/"
    BASE_URL = "https://www.more.com"
    MAX_EVENTS = 5

    engine = ScraperEngine()
    results: list[dict[str, Any]] = []

    logger.info(f"Starting ScraperEngine for {TARGET_URL}...")

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS, follow_redirects=True, timeout=60.0
    ) as client:
        try:
            response = await client.get(TARGET_URL)
            if response.status_code != 200:
                logger.error(f"Listing page fetch failed: {response.status_code}")
                sys.stdout.write("[]\n")
                return

            soup = BeautifulSoup(response.text, "html.parser")

            event_links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                excluded_paths = [
                    r"/offers/",
                    r"/gr-el/tickets/$",
                    r"/tickets/$",
                    r"festival/$",
                    r"music/$",
                    r"theater/$",
                ]
                if (
                    any(re.search(p, href) for p in excluded_paths)
                    or href == "/gr-el/tickets/music/"
                ):
                    continue

                if "/tickets/" in href:
                    if href.startswith("http"):
                        full_url = href
                    elif href.startswith("//"):
                        full_url = f"https:{href}"
                    else:
                        full_url = f"{BASE_URL.rstrip('/')}/{href.lstrip('/')}"
                    event_links.add(full_url)

            links_to_scrape = list(event_links)[:MAX_EVENTS]
            logger.info(f"Scraping top {len(links_to_scrape)} of {len(event_links)} links.")

            if not links_to_scrape:
                logger.warning("No links found to scrape.")
                sys.stdout.write("[]\n")
                return

            tasks = [engine.scrape(link) for link in links_to_scrape]
            scraped_data = await asyncio.gather(*tasks)

            results = [data.model_dump() for data in scraped_data if data]

        except Exception:
            logger.error(f"Fatal Scraper error:\n{traceback.format_exc()}")
        finally:
            sys.stdout.write(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
            logger.info(f"Successfully scraped {len(results)} events.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
