import logging
from datetime import datetime, timedelta

import validators
import requests

from core.config import settings


def get_link(text: str) -> str or None:
    try:
        link = text.split(" ")[1]
        return link
    except Exception:
        return None


def is_time_within_last_n_minutes(
    time_str: str, n: int = settings.LAST_MINUTES_GETTING
) -> bool:
    time_format = "%H:%M"
    try:
        time_provided = (
            datetime.strptime(time_str, time_format) + timedelta(minutes=60)
        ).time()
    except ValueError:
        logging.error(f"Invalid time format: {time_str}")
        return False

    now = datetime.now()
    current_time = now.time()

    # time_provided = (datetime.combine(now.date(), now.time())
    n_minutes_ago = (
        datetime.combine(now.date(), current_time) - timedelta(minutes=n)
    ).time()

    return time_provided >= n_minutes_ago


def is_valid_and_accessible(url: str) -> bool:
    """Check if a URL is valid and returns a successful response."""
    if not validators.url(url):
        return False

    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_valid_url(url: str, fallback_url: str) -> str:
    """Return the provided URL if valid and accessible, otherwise return the fallback URL."""
    return url if is_valid_and_accessible(url) else fallback_url
