import httpx
from bs4 import BeautifulSoup
import json
import asyncio
import logging
import re
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.more.com"
TARGET_URL = "https://www.more.com/gr-el/tickets/music/"
MAX_EVENTS = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
}

def clean_whitespace(text: str) -> str:
    """Collapses multiple spaces, tabs, and newlines into a single space."""
    return re.sub(r'\s+', ' ', text).strip()

async def scrape_event_details(client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
    """
    Fetches an event page and extracts clean content.
    Prioritizes JSON-LD for maximum token efficiency.
    """
    try:
        response = await client.get(url, timeout=15.0)
        
        # Detect Queue-it or other system redirects
        if "queue-it.net" in str(response.url):
            logger.warning(f"Skipping {url}: Redirected to queue system.")
            return None

        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Structured Data Hunt (JSON-LD) - The Gold Standard for tokens
        json_ld_data = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                # If it's a list, extend, else append
                if isinstance(data, list):
                    json_ld_data.extend(data)
                else:
                    json_ld_data.append(data)
            except (json.JSONDecodeError, TypeError):
                continue

        # Filter for Event types in JSON-LD
        events_in_json = [d for d in json_ld_data if d.get("@type") == "Event"]
        if events_in_json:
            return {
                "original_link": url,
                "structured_data": events_in_json[0], # Return the first valid event object
                "source": "json-ld"
            }

        # 2. Targeted Noise Reduction & Extraction Fallback
        # Prune common non-essential elements
        noise_selectors = [
            'header', 'footer', 'nav', 'aside', '.cookie-banner', 
            '.newsletter-signup', '.social-share', 'script', 'style', 'iframe'
        ]
        for element in soup.find_all(noise_selectors):
            element.decompose()

        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        
        if not main_content:
            return None

        raw_text = main_content.get_text(separator=' ', strip=True)
        
        return {
            "original_link": url,
            "raw_text": clean_whitespace(raw_text),
            "source": "html-fallback"
        }

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

async def main():
    logger.info(f"Starting optimized scraper for {TARGET_URL}...")
    
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        try:
            response = await client.get(TARGET_URL, timeout=20.0)
            if response.status_code != 200:
                logger.error(f"Failed to fetch listing page: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            
            event_links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "/tickets/" in href and href != "/gr-el/tickets/music/":
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    event_links.add(full_url)

            # Apply scalability limit
            links_to_scrape = list(event_links)[:MAX_EVENTS]
            logger.info(f"Found {len(event_links)} links. Scraping top {len(links_to_scrape)}.")

            # Batch processing to avoid slamming the server
            tasks = [scrape_event_details(client, link) for link in links_to_scrape]
            scraped_data = await asyncio.gather(*tasks)
            
            results = [data for data in scraped_data if data]

            # Final output
            print(json.dumps(results, indent=2, ensure_ascii=False))
            logger.info(f"Successfully scraped {len(results)} events.")
            
        except Exception as e:
            logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
