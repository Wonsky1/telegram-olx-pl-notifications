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

    DATABASE_URL: str

    URL: str

    DEFAULT_LAST_MINUTES_GETTING: int = 60
    DEFAULT_SENDING_FREQUENCY_MINUTES: float = 0.1
    CHECK_FREQUENCY_SECONDS: int = 10

settings = Settings()
