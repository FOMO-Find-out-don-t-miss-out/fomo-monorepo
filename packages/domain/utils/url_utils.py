from urllib.parse import urlparse


def detect_country_from_url(url: str) -> str:
    """Detect country code from URL domain."""
    if not url:
        return "GR"
    url_lower = url.lower()
    if ".gr" in url_lower or "more.com" in url_lower:
        return "GR"
    if ".de" in url_lower:
        return "DE"
    if ".fr" in url_lower:
        return "FR"
    if ".it" in url_lower:
        return "IT"
    if ".es" in url_lower:
        return "ES"
    if ".nl" in url_lower:
        return "NL"
    if ".at" in url_lower:
        return "AT"
    if ".be" in url_lower:
        return "BE"
    if ".cy" in url_lower:
        return "CY"
    if ".co.uk" in url_lower or "uk." in url_lower:
        return "UK"
    return "GR"


def get_domain_from_url(url: str | None) -> str:
    """Extract domain from URL, removing www."""
    if not url:
        return "unknown"
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "unknown"
    except Exception:
        return "unknown"
