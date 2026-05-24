import logging
from app.crawlers.ggg_trade2_ws import Trade2LiveSearch, OnItemCallback
from app.models.watchlist import WatchlistRule

logger = logging.getLogger(__name__)


class MonitorService:
    """Manages active Trade2 WS connections per watchlist rule."""

    MAX_CONNECTIONS = 20

    def __init__(self, poesessid: str, league: str, on_item: OnItemCallback):
        self._poesessid = poesessid
        self._league = league
        self._on_item = on_item
        self._connections: dict[int, Trade2LiveSearch] = {}

    def is_running(self, rule_id: int) -> bool:
        return rule_id in self._connections

    async def start_rule(self, rule: WatchlistRule):
        if len(self._connections) >= self.MAX_CONNECTIONS:
            raise RuntimeError(f"Max {self.MAX_CONNECTIONS} concurrent connections reached")
        if rule.id in self._connections:
            logger.warning("Rule %d already running, reconnecting", rule.id)
            await self.stop_rule(rule.id)
        query = {
            "query": {
                "status": {"option": "online"},
                "name": rule.item_name or "",
                "type": rule.item_type or "",
            },
            "sort": {"price": "asc"},
        }
        ws = Trade2LiveSearch(self._poesessid, self._league, query, self._on_item)
        await ws.connect()
        self._connections[rule.id] = ws
        logger.info("MonitorService: started rule %d (%s)", rule.id, rule.name)

    async def stop_rule(self, rule_id: int):
        ws = self._connections.pop(rule_id, None)
        if ws:
            await ws.close()
            logger.info("MonitorService: stopped rule %d", rule_id)

    async def close_all(self):
        for ws in list(self._connections.values()):
            await ws.close()
        self._connections.clear()
        logger.info("MonitorService: all connections closed")
