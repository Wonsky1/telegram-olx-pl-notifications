"""Define configuration settings using Pydantic and manage environment variables."""

import os
from logging import getLogger
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


logger = getLogger(__name__)

load_dotenv("dev.env")


class Settings(BaseSettings):
    """Class defining configuration settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    BOT_TOKEN: str
    CHAT_IDS: str

    URL: str = (
        "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/warszawa/?search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=2500&search%5Bfilter_enum_rooms%5D%5B0%5D=one"
    )

    DEFAULT_LAST_MINUTES_GETTING: int = 75
    CHECK_FREQUENCY_SECONDS: int = 10

settings = Settings()
