"""Application configuration via Pydantic Settings + .env file."""

from pydantic_settings import BaseSettings
from typing import ClassVar


class Settings(BaseSettings):
    """All config values, loaded from .env file automatically."""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/poe2.db"

    # Leagues (poe2scout API uses these as LeagueName)
    LEAGUES: str = "Fate of the Vaal,Standard,HC Fate of the Vaal,Hardcore"

    # Crawl intervals (minutes)
    CRAWL_INTERVAL_MINUTES: int = 30
    STASH_INTERVAL_MINUTES: int = 5
    LADDER_INTERVAL_MINUTES: int = 60

    # API keys / secrets
    POE2SCOUT_API_KEY: str = ""
    GGG_POESESSID: str = ""

    # Rate limits
    TRADE2_RATE_LIMIT_RPS: float = 1.0
    POE2SCOUT_RATE_LIMIT_RPS: float = 2.0

    # POE2 realm for poe2scout API
    POE2_REALM: str = "poe2"

    # Base URLs
    POE2SCOUT_BASE: ClassVar[str] = "https://poe2scout.com/api"
    GGG_API_BASE: ClassVar[str] = "https://www.pathofexile.com/api"
    GGG_TRADE2_BASE: ClassVar[str] = "https://www.pathofexile.com/api/trade2"
    POE2DB_URL: ClassVar[str] = "https://poe2db.tw"

    @property
    def league_list(self) -> list[str]:
        return [name.strip() for name in self.LEAGUES.split(",") if name.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
