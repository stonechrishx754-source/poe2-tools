import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import httpx
import websockets

logger = logging.getLogger(__name__)

TRADE2_SEARCH = "https://www.pathofexile.com/api/trade2/search/poe2"
TRADE2_FETCH = "https://www.pathofexile.com/api/trade2/fetch"
TRADE2_LIVE = "wss://www.pathofexile.com/api/trade2/live/poe2"

OnItemCallback = Callable[[dict[str, Any]], Awaitable[None]]


class Trade2LiveSearch:
    """Manages one Trade2 Live Search WebSocket connection."""

    def __init__(
        self,
        poesessid: str,
        league: str,
        query: dict[str, Any],
        on_item: OnItemCallback,
    ):
        self._poesessid = poesessid
        self._league = league
        self._query = query
        self._on_item = on_item
        self._ws = None
        self._query_id: str | None = None
        self._running = False
        self._http: httpx.AsyncClient | None = None
        self._listen_task: asyncio.Task | None = None

    async def connect(self):
        if self._http:
            await self._http.aclose()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._http = httpx.AsyncClient(
            cookies={"POESESSID": self._poesessid},
            timeout=30,
            headers={"User-Agent": "POE2-Analytics/0.1"},
        )
        self._running = True

        resp = await self._http.post(
            f"{TRADE2_SEARCH}/{self._league}",
            json=self._query,
        )
        resp.raise_for_status()
        data = resp.json()
        self._query_id = data["id"]
        logger.info("Trade2WS: search created, query_id=%s, total=%s",
                     self._query_id, data.get("total", "?"))

        ws_url = f"{TRADE2_LIVE}/{self._league}/{self._query_id}"
        self._ws = await websockets.connect(
            ws_url,
            origin="https://www.pathofexile.com",
            extra_headers={"Cookie": f"POESESSID={self._poesessid}"},
            ping_interval=30,
        )
        logger.info("Trade2WS: connected to live search")

        self._listen_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        retry_delay = 5
        while self._running and self._ws:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=60)
                msg = json.loads(raw)
                if "new" not in msg or not self._query_id:
                    continue
                item_ids = msg["new"]
                if not item_ids:
                    continue
                items = await self._fetch_items(item_ids[:10])
                for item in items:
                    await self._on_item(item)
                retry_delay = 5
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                logger.warning("Trade2WS: connection closed, reconnecting in %ds", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
                try:
                    await self.connect()
                except Exception:
                    logger.error("Trade2WS: reconnect failed")
                break
            except Exception as e:
                logger.error("Trade2WS: error in listen loop: %s", e)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    async def _fetch_items(self, item_ids: list[str]) -> list[dict[str, Any]]:
        if not self._http or not self._query_id:
            return []
        ids = ",".join(item_ids)
        resp = await self._http.get(
            f"{TRADE2_FETCH}/{ids}?query={self._query_id}",
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", [])

    async def close(self):
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http:
            await self._http.aclose()
            self._http = None
        logger.info("Trade2WS: closed")
