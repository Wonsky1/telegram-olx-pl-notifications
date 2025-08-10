import httpx


async def is_valid_and_accessible(url: str) -> bool:
    """Check if a URL is valid and returns a successful response."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.status_code == 200
    except Exception:
        return False


def get_link(text: str) -> str | None:
    try:
        link = text.split(" ")[1]
        return link
    except Exception:
        return None


async def get_valid_url(url: str, fallback_url: str) -> str:
    """Return the provided URL if valid and accessible, otherwise return the fallback URL.

    This function is async because it performs an async network check.
    """
    if not url:
        return fallback_url
    return url if await is_valid_and_accessible(url) else fallback_url
