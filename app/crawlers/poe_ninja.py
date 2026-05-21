"""PoeNinja crawler — fetches currency, item, and gem prices."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

LEAGUE_ALIASES = {
    "Dawn of the Hunt": "Dawn+of+the+Hunt",
}


def _encode_league(name: str) -> str:
    """Encode league name for poe.ninja URL (spaces → +)."""
    return LEAGUE_ALIASES.get(name, name.replace(" ", "+"))


class PoeNinjaCrawler(BaseCrawler):
    """Crawls poe.ninja API for currency, item, and gem price data."""

    source_name = "poe_ninja"
    rate_limit_per_second = 0.17   # ~10 req/min
    burst_size = 3

    async def fetch_currency(self, league: str, currency_type: str = "Currency") -> list[dict[str, Any]]:
        """Fetch currency overview from poe.ninja.

        Args:
            league: League name (e.g. "Dawn of the Hunt").
            currency_type: "Currency" or "Fragment".

        Returns:
            List of currency entries with 'currencyTypeName', 'chaosEquivalent', etc.
        """
        url = (
            f"{settings.POE_NINJA_BASE}/currencyoverview"
            f"?league={_encode_league(league)}&type={currency_type}"
        )
        data = await self.fetch(url)
        raw_lines = data.get("lines", [])
        logger.info("poe.ninja: fetched %d %s entries for %s", len(raw_lines), currency_type, league)
        return raw_lines

    async def fetch_items(self, league: str, item_type: str) -> list[dict[str, Any]]:
        """Fetch item overview from poe.ninja.

        Args:
            league: League name.
            item_type: e.g. "UniqueArmour", "UniqueWeapon", "UniqueJewel",
                       "UniqueFlask", "Map", "UniqueAccessory".

        Returns:
            List of item entries with 'name', 'chaosValue', 'divineValue', etc.
        """
        url = (
            f"{settings.POE_NINJA_BASE}/itemoverview"
            f"?league={_encode_league(league)}&type={item_type}"
        )
        data = await self.fetch(url)
        raw_lines = data.get("lines", [])
        logger.info("poe.ninja: fetched %d %s entries for %s", len(raw_lines), item_type, league)
        return raw_lines

    async def fetch_gems(self, league: str, gem_type: str = "SkillGem") -> list[dict[str, Any]]:
        """Fetch gem overview from poe.ninja.

        Args:
            league: League name.
            gem_type: "SkillGem" or "SupportGem".

        Returns:
            List of gem entries with 'name', 'gemLevel', 'chaosValue', etc.
        """
        url = (
            f"{settings.POE_NINJA_BASE}/gemoverview"
            f"?league={_encode_league(league)}&type={gem_type}"
        )
        data = await self.fetch(url)
        raw_lines = data.get("lines", [])
        logger.info("poe.ninja: fetched %d %s entries for %s", len(raw_lines), gem_type, league)
        return raw_lines

    async def fetch_all(self, league: str) -> dict[str, int]:
        """Fetch all data types for a league. Returns counts per category.

        This is the main entry point used by the scheduler.
        """
        now = datetime.now(timezone.utc)
        counts: dict[str, int] = {}

        # Currency
        currency_lines = await self.fetch_currency(league, "Currency")
        frag_lines = await self.fetch_currency(league, "Fragment")
        counts["currency"] = len(currency_lines)
        counts["fragments"] = len(frag_lines)

        # Items
        for item_type in ("UniqueArmour", "UniqueWeapon", "UniqueJewel",
                          "UniqueFlask", "UniqueAccessory", "Map"):
            lines = await self.fetch_items(league, item_type)
            counts[item_type] = len(lines)

        # Gems
        skill_lines = await self.fetch_gems(league, "SkillGem")
        support_lines = await self.fetch_gems(league, "SupportGem")
        counts["SkillGem"] = len(skill_lines)
        counts["SupportGem"] = len(support_lines)

        logger.info(
            "poe.ninja fetch_all for %s complete: %s",
            league,
            {k: v for k, v in counts.items() if v > 0},
        )
        return counts
