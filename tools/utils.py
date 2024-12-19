import logging
import time
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


def get_message_id(message: str) -> str | None:
    """
    Sends a POST request to the API with a given message and retrieves the message_id.

    Args:
        message (str): The message to be included in the payload.

    Returns:
        str: The `message_id` from the API response.

    Raises:
        Exception: If the request fails or the response doesn't contain `message_id`.
    """
    url = f"{settings.API}/ask"
    payload = {"message": message}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        response_data = response.json()

        if "message_id" in response_data:
            return response_data["message_id"]
        else:
            raise ValueError("The response does not contain 'message_id'")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def get_message_from_gpt(message_id: str) -> str | None:
    while True:
        url = f"{settings.API}/get-answer?id={message_id}"
        try:
            response = requests.post(url)
            response.raise_for_status()
            response_data = response.json()

            if "status" in response_data and "message" in response_data:
                status = response_data["status"]
                message = response_data["message"]

                if status == "completed":
                    if message == "Model did not respond, restarting..." or message == "Model did not respond.":
                        return None
                    if message != "I cannot respond to this.":
                        return message
                elif status == "processing":
                    time.sleep(2)
                    continue
                else:
                    return None
            else:
                raise ValueError("The response does not contain status and message")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None


# JSONResponse({"status": "completed", "message": result})
def get_answer_from_gpt(text: str, attempts: int = 5) -> str | None:
    pass