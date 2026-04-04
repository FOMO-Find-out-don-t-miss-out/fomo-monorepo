import argparse
import asyncio
import json
import logging
import sys
import traceback
from typing import Any

from app.services.harvester.factory import ProviderFactory
from app.services.harvester.providers.base import ScrapedEvent

logger = logging.getLogger(__name__)


async def run_scraper(target_url: str, limit: int = 60) -> None:
    """Generic scraping runner using ProviderFactory."""
    factory = ProviderFactory()
    results: list[dict[str, Any]] = []

    logger.info(f"Starting Generic Scraper for {target_url} (limit={limit})...")

    try:
        provider = factory.get_provider(target_url)

        # Phase 1: Discovery
        discovered_links = await provider.discover_links(target_url)
        links_to_scrape = list(set(discovered_links))[:limit]

        logger.info(f"Scraping {len(links_to_scrape)} of {len(discovered_links)} discovered links.")

        if not links_to_scrape:
            logger.warning(f"No links found to scrape for {target_url}.")
            sys.stdout.write("[]\n")
            return

        # Phase 2: Extraction
        async def scrape_one(url: str) -> ScrapedEvent | None:
            p = factory.get_provider(url)
            return await p.fetch_event(url)

        tasks = [scrape_one(link) for link in links_to_scrape]
        scraped_data = await asyncio.gather(*tasks)

        results = [data.model_dump() for data in scraped_data if data]

    except Exception:
        logger.error(f"Fatal Scraper error:\n{traceback.format_exc()}")
    finally:
        sys.stdout.write(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
        logger.info(f"Successfully scraped {len(results)} events.")


def main() -> None:
    """CLI entry point for the scraper."""
    parser = argparse.ArgumentParser(description="FOMO Harvester Scraper CLI")
    parser.add_argument("url", help="Listing page URL to scrape")
    parser.add_argument(
        "--limit", type=int, default=60, help="Maximum number of events to scrape (default: 60)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    asyncio.run(run_scraper(args.url, args.limit))


if __name__ == "__main__":
    main()
