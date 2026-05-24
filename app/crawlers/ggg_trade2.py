"""GGG Trade2 Search API crawler — searches items with 30s cache to respect rate limits."""

import hashlib
import logging
import time
from typing import Any

from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

TRADE2_SEARCH = "https://www.pathofexile.com/api/trade2/search/poe2"
CACHE_TTL = 30


class GggTrade2Crawler(BaseCrawler):
    """Searches GGG Trade2 for items. Caches results for 30s to respect rate limits."""

    source_name = "ggg_trade2"
    rate_limit_per_second = 0.33
    burst_size = 1

    def __init__(self, poesessid: str = ""):
        super().__init__()
        self._poesessid = poesessid or settings.GGG_POESESSID or ""
        self._cache: dict[str, tuple[float, dict]] = {}

    async def search(self, league: str, name: str = "", item_type: str = "",
                     max_price: float | None = None) -> dict[str, Any]:
        if not self._poesessid:
            return {"error": "POESESSID not configured. Set GGG_POESESSID in .env"}

        cache_key = hashlib.md5(f"{league}|{name}|{item_type}|{max_price}".encode()).hexdigest()
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < CACHE_TTL:
                return data

        query_parts: dict[str, Any] = {"status": {"option": "online"}}
        if name:
            query_parts["name"] = name
        if item_type:
            query_parts["type"] = item_type

        body = {"query": query_parts, "sort": {"price": "asc"}}

        try:
            encoded = league.replace(" ", "%20")
            resp = await self.fetch(
                f"{TRADE2_SEARCH}/{encoded}",
                method="POST",
                json_body=body,
                extra_headers={"Cookie": f"POESESSID={self._poesessid}"},
            )
            data = resp if isinstance(resp, dict) else {}
            data["_cached"] = False
            self._cache[cache_key] = (time.time(), data)
            logger.info("GggTrade2: search '%s' -> %s results", name, data.get("total", 0))
            return data
        except Exception as e:
            logger.error("GggTrade2: search failed: %s", e)
            return {"error": str(e)}
