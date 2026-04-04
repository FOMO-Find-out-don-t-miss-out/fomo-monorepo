import logging
from urllib.parse import urlparse

from app.services.harvester.providers.base import BaseProvider
from app.services.harvester.providers.more_com import MoreComProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Maps domains to their respective Provider classes."""

    def __init__(self) -> None:
        self.providers: dict[str, BaseProvider] = {
            "more.com": MoreComProvider(),
        }
        # Default provider for unknown domains
        self.default_provider = MoreComProvider()

    def get_provider(self, url: str) -> BaseProvider:
        domain = urlparse(url).netloc.replace("www.", "")
        return self.providers.get(domain, self.default_provider)
