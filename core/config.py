"""Define configuration settings using Pydantic and manage environment variables."""

from logging import getLogger

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)

load_dotenv("dev.env")


class Settings(BaseSettings):
    """Class defining configuration settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    BOT_TOKEN: str
    CHAT_IDS: str

    CHECK_FREQUENCY_SECONDS: int = 10

    TOPN_DB_BASE_URL: str

    # DB settings
    DB_REMOVE_OLD_ITEMS_DATA_N_DAYS: int = 7

    # Redis settings for state persistence
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


settings = Settings()
