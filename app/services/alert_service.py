import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class AlertService:
    """asyncio.Queue-based event bus for SSE deal notifications."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    async def push(self, deal: dict):
        try:
            self._queue.put_nowait(deal)
        except asyncio.QueueFull:
            logger.warning("AlertService: queue full, dropping deal")

    async def stream(self):
        while True:
            try:
                deal = await asyncio.wait_for(self._queue.get(), timeout=30)
                yield {
                    "event": "new-deal",
                    "data": json.dumps(deal, ensure_ascii=False),
                }
            except asyncio.TimeoutError:
                yield {"event": "heartbeat", "data": "{}"}
