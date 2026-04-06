import secrets

# Randomized realistic User-Agents
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",  # noqa: E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",  # noqa: E501
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",  # noqa: E501
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",  # noqa: E501
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",  # noqa: E501
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Mobile Safari (iPhone)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",  # noqa: E501
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",  # noqa: E501
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",  # noqa: E501
]

ACCEPT_LANGUAGES = [
    "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8,el;q=0.7",
    "el,en;q=0.9",
]


def get_rotated_headers() -> dict[str, str]:
    """
    Returns a randomized set of realistic Browser Headers.
    """
    rng = secrets.SystemRandom()
    ua = rng.choice(USER_AGENTS)
    lang = rng.choice(ACCEPT_LANGUAGES)

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
        "Accept-Language": lang,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": rng.choice(["?1", "none"]),
    }

    # Add platform-specific Sec-Ch-Ua headers for Chrome/Edge if detected in UA
    if "Chrome" in ua or "Edg" in ua:
        headers["Sec-Ch-Ua-Mobile"] = "?1" if "Mobile" in ua else "?0"
        if "Windows" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"Windows"'
        elif "Macintosh" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"macOS"'
        elif "Android" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"Android"'
        elif "Linux" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"Linux"'

    return headers
