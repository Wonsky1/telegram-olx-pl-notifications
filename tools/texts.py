import validators
import requests


def is_valid_and_accessible(url: str) -> bool:
    """Check if a URL is valid and returns a successful response."""
    if not validators.url(url):
        return False

    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_link(text: str) -> str | None:
    try:
        link = text.split(" ")[1]
        return link
    except Exception:
        return None

def get_valid_url(url: str, fallback_url: str) -> str:
    """Return the provided URL if valid and accessible, otherwise return the fallback URL."""
    if not url:
        return fallback_url
    return url if is_valid_and_accessible(url) else fallback_url
