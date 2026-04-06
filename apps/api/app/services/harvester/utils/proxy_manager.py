import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_proxy_config() -> dict[str, Any] | None:
    """
    Returns an httpx compatible proxy dictionary: {"http://": proxy_url, "https://": proxy_url}.
    Includes logic to log (at DEBUG level) whether a proxy is being used or if the scraper is
    running on the 'Direct IP' (fallback).
    """
    proxy_url = settings.SCRAPER_PROXY_URL

    if not proxy_url:
        logger.debug("Harvester is running on 'Direct IP' (fallback). No proxy configured.")
        return None

    logger.debug(f"Harvester is using proxy: {proxy_url}")
    return {
        "http://": proxy_url,
        "https://": proxy_url,
    }
