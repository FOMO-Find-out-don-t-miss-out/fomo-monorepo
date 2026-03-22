import httpx
from bs4 import BeautifulSoup
import json
import logging
import re
import os
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

class ScrapedEvent(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    original_link: str
    country_code: str
    source: str
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class BaseExtractor:
    async def extract(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class SchemaOrgExtractor(BaseExtractor):
    """Extracts data using JSON-LD schema.org objects."""
    async def extract(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Event" or "Event" in str(item.get("@type", "")):
                        return {
                            "structured_data": item,
                            "source": "schema_org"
                        }
            except (json.JSONDecodeError, TypeError):
                continue
        return None

class RegistryExtractor(BaseExtractor):
    """Extracts data using site-specific CSS selectors from registry.json."""
    def __init__(self, registry: Dict[str, Any]):
        self.registry = registry

    async def extract(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        domain = urlparse(url).netloc.replace("www.", "")
        config = self.registry.get(domain)
        if not config or "selectors" not in config:
            return None

        selectors = config["selectors"]
        extracted = {}
        for field, selector in selectors.items():
            element = soup.select_one(selector)
            if element:
                if element.name == "time" and element.has_attr("datetime"):
                    extracted[field] = element["datetime"]
                else:
                    extracted[field] = element.get_text(strip=True)

        if extracted:
            return {
                "extracted_fields": extracted,
                "source": "registry"
            }
        return None

class ScraperEngine:
    def __init__(self, registry_path: str = "app/services/harvester/registry.json"):
        self.registry = self._load_registry(registry_path)
        self.schema_extractor = SchemaOrgExtractor()
        self.registry_extractor = RegistryExtractor(self.registry)
        self.tld_to_country = {
            "gr": "GR", "uk": "GB", "de": "DE", "fr": "FR", 
            "it": "IT", "es": "ES", "us": "US", "com": "US"
        }

    def _load_registry(self, path: str) -> Dict[str, Any]:
        # Try relative to the file if absolute fails
        if not os.path.isabs(path):
            base_dir = os.path.dirname(__file__)
            path = os.path.join(base_dir, "registry.json")
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load registry from {path}: {e}")
            return {}

    def _get_country_code(self, url: str) -> str:
        domain = urlparse(url).netloc.replace("www.", "")
        # 1. From Registry
        if domain in self.registry:
            return self.registry[domain].get("country_code", "US")
        
        # 2. From TLD
        tld = domain.split(".")[-1].lower()
        return self.tld_to_country.get(tld, "US")

    async def scrape(self, url: str) -> Optional[ScrapedEvent]:
        try:
            async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                country_code = self._get_country_code(url)

                # Strategy 1: Registry (Site-specific rules)
                registry_data = await self.registry_extractor.extract(soup, url)
                if registry_data:
                    fields = registry_data["extracted_fields"]
                    return ScrapedEvent(
                        title=fields.get("title"),
                        description=fields.get("description"),
                        location_name=fields.get("location"),
                        start_time=fields.get("start_time"),
                        end_time=fields.get("end_time"),
                        original_link=url,
                        country_code=country_code,
                        source="registry"
                    )

                # Strategy 2: Schema.org (JSON-LD)
                schema_data = await self.schema_extractor.extract(soup, url)
                if schema_data:
                    sd = schema_data["structured_data"]
                    return ScrapedEvent(
                        title=sd.get("name"),
                        description=sd.get("description"),
                        location_name=sd.get("location", {}).get("name") if isinstance(sd.get("location"), dict) else sd.get("location"),
                        start_time=sd.get("startDate"),
                        end_time=sd.get("endDate"),
                        original_link=url,
                        country_code=country_code,
                        source="schema_org",
                        structured_data=sd
                    )

                # Strategy 3: LLM Fallback (Minimal Clean HTML)
                noise_selectors = ['header', 'footer', 'nav', 'aside', 'script', 'style']
                for element in soup.find_all(noise_selectors):
                    element.decompose()
                
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                raw_text = re.sub(r'\s+', ' ', main_content.get_text(separator=' ', strip=True)).strip()
                
                return ScrapedEvent(
                    original_link=url,
                    country_code=country_code,
                    source="llm_fallback",
                    raw_text=raw_text[:5000] # Limit for LLM context
                )

        except Exception as e:
            logger.error(f"ScraperEngine error for {url}: {e}")
            return None

async def main():
    import argparse
    import sys
    import traceback

    # Basic setup for CLI usage
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr # Ensure logs go to stderr so stdout is only for JSON
    )
    
    TARGET_URL = "https://www.more.com/gr-el/tickets/music/"
    BASE_URL = "https://www.more.com"
    MAX_EVENTS = 20

    engine = ScraperEngine()
    results = []
    
    logger.info(f"Starting ScraperEngine for {TARGET_URL}...")
    
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=60.0) as client:
        try:
            response = await client.get(TARGET_URL)
            if response.status_code != 200:
                logger.error(f"Failed to fetch listing page: {response.status_code} - {response.text[:200]}")
                # Print empty list to avoid JSON parse errors
                print("[]")
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            
            event_links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # Exclude obvious non-event pages and broad category indexes
                excluded_paths = [r"/offers/", r"/gr-el/tickets/$", r"/tickets/$", r"festival/$", r"music/$", r"theater/$"]
                if any(re.search(pattern, href) for pattern in excluded_paths) or href == "/gr-el/tickets/music/":
                    continue
                    
                if "/tickets/" in href:
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    event_links.add(full_url)

            links_to_scrape = list(event_links)[:MAX_EVENTS]
            logger.info(f"Found {len(event_links)} links. Scraping top {len(links_to_scrape)}.")

            if not links_to_scrape:
                logger.warning("No links found to scrape.")
                print("[]")
                return

            tasks = [engine.scrape(link) for link in links_to_scrape]
            scraped_data = await asyncio.gather(*tasks)
            
            results = [data.model_dump() for data in scraped_data if data]
            
        except Exception as e:
            logger.error(f"An error occurred in main:\n{traceback.format_exc()}")
        finally:
            # Final output for subprocess parsing - ALWAYS print a list
            print(json.dumps(results, indent=2, ensure_ascii=False))
            logger.info(f"Successfully scraped {len(results)} events.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
