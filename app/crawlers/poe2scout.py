"""POE2 Scout crawler — fetches currency, item, and price data from poe2scout.com API."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

BASE = settings.POE2SCOUT_BASE
REALM = settings.POE2_REALM


class Poe2ScoutCrawler(BaseCrawler):
    """Crawls poe2scout.com API for POE2 economic data.

    API docs: https://poe2scout.com/api/swagger
    Rate limit: ~2 requests/second (be respectful).
    """

    source_name = "poe2scout"
    rate_limit_per_second = settings.POE2SCOUT_RATE_LIMIT_RPS
    burst_size = 3

    async def _get(self, path: str) -> dict[str, Any] | list[Any]:
        url = f"{BASE}{path}"
        return await self.fetch(url, headers={"User-Agent": "POE2-Analytics/0.1"})

    async def fetch_leagues(self) -> list[dict[str, Any]]:
        """GET /{Realm}/Leagues — list all leagues with prices."""
        data = await self._get(f"/{REALM}/Leagues")
        if isinstance(data, list):
            logger.info("poe2scout: fetched %d leagues", len(data))
            return data
        return []

    async def fetch_currencies_by_category(self, league: str) -> list[dict[str, Any]]:
        """GET /{Realm}/Leagues/{LeagueName}/Currencies/ByCategory.

        Returns currencies grouped by category with prices.
        """
        from urllib.parse import quote
        encoded = quote(league)
        data = await self._get(f"/{REALM}/Leagues/{encoded}/Currencies/ByCategory")
        if isinstance(data, list):
            logger.info("poe2scout: fetched %d currency categories for %s", len(data), league)
            return data
        return []

    async def fetch_exchange_snapshot(self, league: str) -> dict[str, Any]:
        """GET /{Realm}/Leagues/{LeagueName}/ExchangeSnapshot.

        Returns exchange rate snapshot with volume and market cap.
        """
        from urllib.parse import quote
        encoded = quote(league)
        data = await self._get(f"/{REALM}/Leagues/{encoded}/ExchangeSnapshot")
        if isinstance(data, dict):
            return data
        return {}

    async def fetch_reference_currencies(self, league: str) -> list[dict[str, Any]]:
        """GET /{Realm}/Leagues/{LeagueName}/ReferenceCurrencies.

        Returns reference currency list with base prices.
        """
        from urllib.parse import quote
        encoded = quote(league)
        data = await self._get(f"/{REALM}/Leagues/{encoded}/ReferenceCurrencies")
        if isinstance(data, list):
            return data
        return []

    async def fetch_items(self, league: str) -> list[dict[str, Any]]:
        """GET /{Realm}/Leagues/{LeagueName}/Items.

        Returns all items with current prices.
        """
        from urllib.parse import quote
        encoded = quote(league)
        data = await self._get(f"/{REALM}/Leagues/{encoded}/Items")
        if isinstance(data, list):
            logger.info("poe2scout: fetched %d items for %s", len(data), league)
            return data
        return []

    async def fetch_uniques_by_category(self, league: str) -> list[dict[str, Any]]:
        """GET /{Realm}/Leagues/{LeagueName}/Uniques/ByCategory.

        Returns unique items grouped by category with prices.
        NOTE: This endpoint may require additional parameters.
        Falls back to empty list on error.
        """
        try:
            from urllib.parse import quote
            encoded = quote(league)
            data = await self._get(f"/{REALM}/Leagues/{encoded}/Uniques/ByCategory")
            if isinstance(data, list):
                logger.info("poe2scout: fetched %d unique categories for %s", len(data), league)
                return data
        except Exception as e:
            logger.warning("poe2scout: uniques endpoint failed for %s: %s", league, e)
        return []

    async def fetch_item_categories(self, league: str) -> list[str]:
        """GET /{Realm}/Leagues/{LeagueName}/Items/Categories."""
        from urllib.parse import quote
        encoded = quote(league)
        data = await self._get(f"/{REALM}/Leagues/{encoded}/Items/Categories")
        if isinstance(data, list):
            return data
        return []

    async def fetch_all(self, league: str) -> dict[str, int]:
        """Fetch all data for a league. Returns counts per category."""
        now = datetime.now(timezone.utc)
        counts: dict[str, int] = {}

        # Currencies
        currencies = await self.fetch_currencies_by_category(league)
        counts["currencies"] = len(currencies)

        # Uniques
        uniques = await self.fetch_uniques_by_category(league)
        counts["uniques"] = len(uniques)

        # All items (for item overview)
        items = await self.fetch_items(league)
        counts["items"] = len(items)

        # Reference currencies (for exchange rates)
        ref_currencies = await self.fetch_reference_currencies(league)
        counts["reference_currencies"] = len(ref_currencies)

        # Exchange snapshot
        exchange = await self.fetch_exchange_snapshot(league)
        counts["exchange_available"] = 1 if exchange else 0

        logger.info(
            "poe2scout fetch_all for '%s' complete: %s",
            league, counts,
        )
        return counts
