import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.harvester.providers.base import BaseProvider, ScrapedEvent

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


class MoreComProvider(BaseProvider):
    def __init__(self, registry_path: str | None = None) -> None:
        self.registry = self._load_registry(registry_path)
        self.base_url = "https://www.more.com"
        self.excluded_paths = [
            r"/offers/",
            r"/gr-el/tickets/$",
            r"/tickets/$",
            r"festival/$",
            r"music/$",
            r"theater/$",
        ]
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

    async def discover_links(self, target_url: str) -> list[str]:
        """Discovery logic for more.com listing pages."""
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS, follow_redirects=True, timeout=60.0
            ) as client:
                response = await client.get(target_url)
                if response.status_code != 200:
                    logger.error(f"Discovery fetch failed for {target_url}: {response.status_code}")
                    return []

                soup = BeautifulSoup(response.text, "html.parser")
                event_links = set()

                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()

                    # Filter based on regex and listing page URL
                    if any(re.search(p, href) for p in self.excluded_paths) or href == target_url:
                        continue

                    if "/tickets/" in href:
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("//"):
                            full_url = f"https:{href}"
                        else:
                            full_url = f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"
                        event_links.add(full_url)

                return list(event_links)

        except Exception as e:
            logger.error(f"Discovery error for {target_url}: {e}")
            return []

    def _load_registry(self, path_str: str | None) -> dict[str, Any]:
        if path_str:
            path = Path(path_str)
        else:
            # Look for registry.json in the harvester directory (one level up from providers/)
            path = Path(__file__).parent.parent / "registry.json"

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

    def _normalize_url(self, u: str | None, base: str) -> str | None:
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

    def _ensure_string(self, val: object) -> str | None:
        if val is None:
            return None
        if isinstance(val, list):
            if not val or val[0] is None:
                return None
            return str(val[0])
        return str(val)

    async def fetch_event(self, url: str) -> ScrapedEvent | None:
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0
            ) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

                soup = BeautifulSoup(response.text, "html.parser")
                country_code = self._get_country_code(url)
                urlparse(url)

                # 1. Registry Extraction
                registry_data = await self._extract_registry(soup, url)
                if registry_data:
                    fields = registry_data["extracted_fields"]
                    return ScrapedEvent(
                        title=self._ensure_string(fields.get("title")),
                        description=None,
                        location_name=self._ensure_string(fields.get("location")),
                        start_time=self._ensure_string(fields.get("start_time")),
                        end_time=self._ensure_string(fields.get("end_time")),
                        photo_url=None,
                        original_link=url,
                        country_code=country_code,
                        source="registry",
                        source_provider="more.com",
                        ingestion_method="registry",
                    )

                # 2. Schema.org Extraction
                schema_data = await self._extract_schema_org(soup)
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
                        title=self._ensure_string(sd.get("name")),
                        description=None,
                        location_name=self._ensure_string(loc_name),
                        start_time=self._ensure_string(sd.get("startDate")),
                        end_time=self._ensure_string(sd.get("endDate")),
                        photo_url=None,
                        original_link=url,
                        country_code=country_code,
                        source="schema_org",
                        source_provider="more.com",
                        ingestion_method="json_ld",
                        structured_data=sd,
                    )

                # 3. LLM Fallback (Text extraction)
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
                    description=None,
                    photo_url=None,
                    original_link=url,
                    country_code=country_code,
                    source="llm_fallback",
                    source_provider="more.com",
                    ingestion_method="html_fallback",
                    raw_text=raw_text[:5000],
                )

        except Exception as e:
            logger.error(f"MoreComProvider error for {url}: {e}")
            return None

    async def _extract_registry(self, soup: BeautifulSoup, url: str) -> dict[str, Any] | None:
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

    async def _extract_schema_org(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("@type") == "Event" or "Event" in str(item.get("@type", "")):
                        return {
                            "structured_data": item,
                            "photo_url": None,
                            "source": "schema_org",
                        }
            except (json.JSONDecodeError, TypeError):
                continue
        return None
