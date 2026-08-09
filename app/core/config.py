from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    DATABASE_URL: str = ""

    APP_NAME: str = "SharpStack"

    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings():

    settings = Settings()

    if not settings.DATABASE_URL:
        raise RuntimeError(
            "\nDATABASE_URL is missing from your .env file.\n"
            "Please add your Azure PostgreSQL connection string."
        )

    return settings


settings = get_settings()
