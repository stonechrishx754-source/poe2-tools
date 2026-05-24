"""GGG Public Stash API crawler — polls stash-tab river with next_change_id cursor."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

STASH_API = "https://www.pathofexile.com/api/public-stash-tabs"


class GggStashCrawler(BaseCrawler):
    """Polls GGG Public Stash API with next_change_id cursor."""

    source_name = "ggg_stash"
    rate_limit_per_second = 1.0
    burst_size = 3

    def __init__(self):
        super().__init__()
        self.next_change_id: str | None = None

    async def load_cursor(self):
        try:
            with open("data/stash_cursor.txt") as f:
                self.next_change_id = f.read().strip() or None
        except FileNotFoundError:
            self.next_change_id = None

    def save_cursor(self):
        with open("data/stash_cursor.txt", "w") as f:
            f.write(self.next_change_id or "")

    async def poll(self) -> tuple[list[dict[str, Any]], str | None]:
        url = STASH_API
        if self.next_change_id:
            url += f"?id={self.next_change_id}"
        data = await self.fetch(url)
        new_cursor = data.get("next_change_id")
        stashes = data.get("stashes", [])
        priced_items: list[dict[str, Any]] = []
        for stash in stashes:
            for item in stash.get("items", []):
                note = item.get("note", "")
                if not note or "~price" not in note:
                    continue
                item["_account"] = stash.get("accountName", "")
                item["_character"] = stash.get("lastCharacterName", "")
                item["_stash_id"] = stash.get("id", "")
                item["_stash_type"] = stash.get("stashType", "")
                priced_items.append(item)
        logger.info("ggg_stash: %d stashes, %d priced items", len(stashes), len(priced_items))
        return priced_items, new_cursor
