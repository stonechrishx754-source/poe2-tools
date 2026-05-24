# Phase 2: Real-Time Trade Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public stash crawling and a real-time trade monitoring system with SSE push notifications.

**Architecture:** Four new ORM models feed two crawlers (stash polling + Trade2 WebSocket). A MonitorService manages WS connections per watchlist rule, DealService computes discount rates from market data, and AlertService broadcasts via SSE to the browser. UI is a dedicated /monitor page with left sidebar (rules) and right feed (deals).

**Tech Stack:** Python FastAPI, SQLAlchemy 2.0 + aiosqlite, `websockets` library, `sse-starlette`, Jinja2/HTMX

**Spec:** `docs/superpowers/specs/2026-05-24-phase2-monitor-design.md`

---

## File Structure

### Create
| File | Responsibility |
|------|---------------|
| `app/models/stash.py` | Public stash tab + priced items ORM |
| `app/models/watchlist.py` | User monitoring rules ORM |
| `app/models/deal_alert.py` | Detected deal opportunities ORM |
| `app/models/purchase_log.py` | Completed purchase records ORM |
| `app/crawlers/ggg_stash.py` | GGG Public Stash API poller |
| `app/crawlers/ggg_trade2_ws.py` | Trade2 Live Search WebSocket client |
| `app/services/monitor_service.py` | WS connection lifecycle manager |
| `app/services/deal_service.py` | Price discount calculation engine |
| `app/services/alert_service.py` | asyncio.Queue + SSE broadcast |
| `app/routers/api_monitor.py` | SSE endpoint + watchlist/deal CRUD |
| `app/templates/monitor.html` | Left-right split monitor dashboard |

### Modify
| File | Change |
|------|--------|
| `app/models/__init__.py` | Add new model imports |
| `app/routers/web.py` | Add `/monitor`, `/watchlist` HTML routes |
| `app/scheduler.py` | Add stash crawl job |
| `app/templates/base.html` | Add Monitor nav link |
| `app/translations.py` | Add monitor-related keys |
| `app/config.py` | Add stash/ws interval settings |
| `.env` | Add GGG_POESESSID |

---

### Task 1: New Data Models

**Files:**
- Create: `app/models/stash.py`
- Create: `app/models/watchlist.py`
- Create: `app/models/deal_alert.py`
- Create: `app/models/purchase_log.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Create stash model**

```python
# app/models/stash.py
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class StashTab(Base):
    __tablename__ = "stash_tabs"

    id: Mapped[int] = mapped_column(primary_key=True)
    stash_id: Mapped[str] = mapped_column(String(128), unique=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    account_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stash_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Create watchlist model**

```python
# app/models/watchlist.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WatchlistRule(Base):
    __tablename__ = "watchlist_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    item_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_discount: Mapped[float] = mapped_column(Float, default=0.15)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_sound: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_browser: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_copy_whisper: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: Create deal_alert model**

```python
# app/models/deal_alert.py
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DealAlert(Base):
    __tablename__ = "deal_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    trade2_id: Mapped[str] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(128))
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seller_character: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_amount: Mapped[float] = mapped_column(Float, nullable=False)
    price_currency: Mapped[str] = mapped_column(String(32), default="chaos")
    market_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    whisper_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Create purchase_log model**

```python
# app/models/purchase_log.py
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PurchaseLog(Base):
    __tablename__ = "purchase_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_alert_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_name: Mapped[str] = mapped_column(String(128))
    price_amount: Mapped[float] = mapped_column(Float)
    price_currency: Mapped[str] = mapped_column(String(32), default="chaos")
    market_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    seller_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 5: Update models __init__.py**

```python
# app/models/__init__.py — append new imports
from app.models.stash import StashTab
from app.models.watchlist import WatchlistRule
from app.models.deal_alert import DealAlert
from app.models.purchase_log import PurchaseLog
```

- [ ] **Step 6: Create tables and verify**

```bash
cd E:/project-poe2 && python -c "
import asyncio
from app.database import engine
from app.models.base import Base

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created')

asyncio.run(init())
"
```

Expected: `Tables created`

---

### Task 2: GGG Public Stash Crawler

**Files:**
- Create: `app/crawlers/ggg_stash.py`
- Modify: `app/scheduler.py`

- [ ] **Step 1: Create GggStashCrawler**

```python
# app/crawlers/ggg_stash.py
import json
import logging
from datetime import datetime, timezone
from typing import Any
from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

STASH_API = "https://www.pathofexile.com/api/public-stash-tabs"


class GggStashCrawler(BaseCrawler):
    """Polls GGG Public Stash API with next_change_id cursor.
    Extracts items with price notes into structured data.
    """

    source_name = "ggg_stash"
    rate_limit_per_second = 1.0
    burst_size = 3

    def __init__(self):
        super().__init__()
        self.next_change_id: str | None = None

    async def load_cursor(self):
        """Load last known next_change_id from file."""
        try:
            with open("data/stash_cursor.txt") as f:
                self.next_change_id = f.read().strip() or None
        except FileNotFoundError:
            self.next_change_id = None

    def save_cursor(self):
        with open("data/stash_cursor.txt", "w") as f:
            f.write(self.next_change_id or "")

    async def poll(self) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch one batch of public stash tabs.

        Returns (priced_items, next_change_id_or_None).
        priced_items is a flat list of items with price notes.
        """
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

        logger.info("ggg_stash: %d stashes, %d priced items, cursor=%s",
                     len(stashes), len(priced_items),
                     str(new_cursor)[:30] if new_cursor else "None")
        return priced_items, new_cursor
```

- [ ] **Step 2: Add stash crawl job to scheduler**

```python
# In app/scheduler.py, add after the crawl_data function:

from app.crawlers.ggg_stash import GggStashCrawler

async def crawl_stash():
    """Scheduled: poll GGG Public Stash API."""
    crawler = GggStashCrawler()
    await crawler.load_cursor()

    start = datetime.now(timezone.utc)
    error_msg = None

    try:
        items, new_cursor = await crawler.poll()
        if new_cursor:
            crawler.next_change_id = new_cursor
            crawler.save_cursor()
        # For now, just log; Phase 3 will save to stash_items table
        logger.info("ggg_stash: polled %d priced items", len(items))
    except Exception as e:
        error_msg = str(e)
        logger.error("ggg_stash poll failed: %s", e)
    finally:
        await crawler.close()

# In start_scheduler(), add:
    scheduler.add_job(
        crawl_stash,
        "interval",
        minutes=settings.STASH_INTERVAL_MINUTES,
        id="stash_poll",
        max_instances=1,
        replace_existing=True,
    )
```

- [ ] **Step 3: Add STASH_INTERVAL_MINUTES to config**

```python
# In app/config.py, ensure this line exists:
STASH_INTERVAL_MINUTES: int = 5
```

---

### Task 3: Trade2 WebSocket Client

**Files:**
- Create: `app/crawlers/ggg_trade2_ws.py`

- [ ] **Step 1: Create the WebSocket crawler**

```python
# app/crawlers/ggg_trade2_ws.py
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
    """Manages one Trade2 Live Search WebSocket connection.

    Usage:
        ws = Trade2LiveSearch("POESESSID_value", "Fate of the Vaal",
                              query_json_dict, on_item_callback)
        await ws.connect()   # POSTs search, opens WS, listens
        await ws.close()     # clean shutdown
    """

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

    async def connect(self):
        """POST a search, then open WebSocket to listen for new results."""
        self._http = httpx.AsyncClient(cookies={"POESESSID": self._poesessid})
        self._running = True

        # Step 1: POST search query
        resp = await self._http.post(
            f"{TRADE2_SEARCH}/{self._league}",
            json=self._query,
        )
        resp.raise_for_status()
        data = resp.json()
        self._query_id = data["id"]
        logger.info("Trade2WS: search created, query_id=%s, total=%s",
                     self._query_id, data.get("total", "?"))

        # Step 2: Open WebSocket
        ws_url = f"{TRADE2_LIVE}/{self._league}/{self._query_id}"
        self._ws = await websockets.connect(
            ws_url,
            origin="https://www.pathofexile.com",
            extra_headers={"Cookie": f"POESESSID={self._poesessid}"},
            ping_interval=30,
        )
        logger.info("Trade2WS: connected to %s", ws_url)

        # Step 3: Listen loop
        asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        """Continuously read WS messages, fetch item details, call on_item."""
        while self._running and self._ws:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=60)
                msg = json.loads(raw)
                if "new" in msg and self._query_id:
                    item_ids = msg["new"]
                    items = await self._fetch_items(item_ids[:10])
                    for item in items:
                        await self._on_item(item)
            except asyncio.TimeoutError:
                continue  # heartbeat, ok
            except websockets.ConnectionClosed:
                logger.warning("Trade2WS: connection closed, reconnecting in 10s")
                await asyncio.sleep(10)
                try:
                    await self.connect()
                except Exception:
                    logger.error("Trade2WS: reconnect failed")
                break
            except Exception as e:
                logger.error("Trade2WS: error in listen loop: %s", e)
                await asyncio.sleep(5)

    async def _fetch_items(self, item_ids: list[str]) -> list[dict[str, Any]]:
        """Call Trade2 Fetch API to get full item details."""
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
        """Graceful shutdown."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http:
            await self._http.aclose()
            self._http = None
        logger.info("Trade2WS: closed")
```

---

### Task 4: Monitor Service (WS Connection Manager)

**Files:**
- Create: `app/services/monitor_service.py`

- [ ] **Step 1: Create MonitorService**

```python
# app/services/monitor_service.py
import logging
from app.crawlers.ggg_trade2_ws import Trade2LiveSearch, OnItemCallback
from app.models.watchlist import WatchlistRule

logger = logging.getLogger(__name__)


class MonitorService:
    """Manages active Trade2 WS connections per watchlist rule.

    Tracks which rules have live connections, starts/stops them,
    and enforces the ~20 concurrent connection limit.

    Usage:
        svc = MonitorService(poesessid, league, on_item_callback)
        await svc.start_rule(rule)    # opens WS for rule
        await svc.stop_rule(rule_id)  # closes WS for rule
        await svc.close_all()         # shutdown all
    """

    MAX_CONNECTIONS = 20

    def __init__(self, poesessid: str, league: str, on_item: OnItemCallback):
        self._poesessid = poesessid
        self._league = league
        self._on_item = on_item
        self._connections: dict[int, Trade2LiveSearch] = {}

    def is_running(self, rule_id: int) -> bool:
        return rule_id in self._connections

    async def start_rule(self, rule: WatchlistRule):
        """Start monitoring a rule. Opens a Trade2 WebSocket."""
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

        ws = Trade2LiveSearch(
            self._poesessid, self._league, query, self._on_item,
        )
        await ws.connect()
        self._connections[rule.id] = ws
        logger.info("MonitorService: started rule %d (%s)", rule.id, rule.name)

    async def stop_rule(self, rule_id: int):
        """Stop monitoring a rule. Closes the WebSocket."""
        ws = self._connections.pop(rule_id, None)
        if ws:
            await ws.close()
            logger.info("MonitorService: stopped rule %d", rule_id)

    async def close_all(self):
        for ws in list(self._connections.values()):
            await ws.close()
        self._connections.clear()
        logger.info("MonitorService: all connections closed")
```

---

### Task 5: Deal Detection Service

**Files:**
- Create: `app/services/deal_service.py`

- [ ] **Step 1: Create DealService**

```python
# app/services/deal_service.py
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.deal_alert import DealAlert
from app.models.item import ItemSnapshot

logger = logging.getLogger(__name__)


class DealService:
    """Evaluates incoming Trade2 items against watchlist rules.

    For each item: extracts price, computes market average, calculates
    discount percentage, and if it meets the threshold, creates a
    DealAlert and pushes to the alert queue.
    """

    def __init__(self, league_id: int, alert_queue):
        self._league_id = league_id
        self._alert_queue = alert_queue

    async def evaluate(self, rule_id: int, rule_max_price: float | None,
                       rule_min_discount: float, item: dict[str, Any]):
        """Evaluate one item from a Trade2 WS push."""
        listing = item.get("listing", {})
        price_data = listing.get("price", {})
        item_data = item.get("item", {})

        price_amount = price_data.get("amount")
        price_currency = price_data.get("currency", "chaos")
        item_name = (item_data.get("name") or
                     item_data.get("typeLine", ""))
        item_type = item_data.get("typeLine", "")

        if not price_amount or not item_name:
            return

        price_amount = float(price_amount)

        # Check max price
        if rule_max_price and price_amount > rule_max_price:
            return

        # Compute market average from our database
        market_avg = await self._get_market_avg(item_name)
        if market_avg is None or market_avg <= 0:
            logger.debug("DealService: no market data for %s, skipping", item_name)
            return

        # Calculate discount
        discount_pct = (market_avg - price_amount) / market_avg
        if discount_pct < rule_min_discount:
            return

        # Generate trade URL
        trade2_id = hashlib.md5(item_name.encode()).hexdigest()[:12]
        trade_url = (
            f"https://www.pathofexile.com/trade2/search/poe2/"
            f"Fate%20of%20the%20Vaal/{trade2_id}"
        )
        whisper = listing.get("whisper", "")

        # Create deal alert
        async with AsyncSessionLocal() as db:
            alert = DealAlert(
                rule_id=rule_id,
                trade2_id=str(item.get("id", "")),
                item_name=item_name,
                item_type=item_type,
                item_json=str(item),
                seller_account=listing.get("account", {}).get("name", ""),
                seller_character=listing.get("account", {}).get("lastCharacterName", ""),
                price_amount=price_amount,
                price_currency=price_currency,
                market_avg=round(market_avg, 2),
                discount_pct=round(discount_pct * 100, 1),
                whisper_message=whisper,
                trade_url=trade_url,
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)

            # Push to SSE alert queue
            msg = {
                "id": alert.id,
                "item_name": item_name,
                "price_amount": price_amount,
                "price_currency": price_currency,
                "market_avg": round(market_avg, 2),
                "discount_pct": round(discount_pct * 100, 1),
                "seller": listing.get("account", {}).get("name", ""),
                "whisper_message": whisper,
                "trade_url": trade_url,
            }
            await self._alert_queue.put(msg)
            logger.info("DealService: ALERT %s %.1f%% OFF (%s vs %s)",
                         item_name, discount_pct * 100, price_amount, market_avg)

    async def _get_market_avg(self, item_name: str) -> float | None:
        """Get average price from our item snapshots table."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.avg(ItemSnapshot.chaos_value))
                .where(ItemSnapshot.item_name == item_name)
            )
            avg = result.scalar()
            return float(avg) if avg else None
```

---

### Task 6: Alert Service (SSE Broadcast)

**Files:**
- Create: `app/services/alert_service.py`

- [ ] **Step 1: Create AlertService**

```python
# app/services/alert_service.py
import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AlertService:
    """Event bus for SSE deal notifications.

    Components push deal dicts to the queue; the SSE endpoint
    reads from it and sends to connected browser clients.

    Usage:
        svc = AlertService()
        await svc.push({"item_name": "...", ...})  # producers call this
        async for event in svc.stream():            # SSE endpoint calls this
            yield event
    """

    def __init__(self):
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)

    async def push(self, deal: dict[str, Any]):
        """Push a deal to the broadcast queue. Non-blocking if full."""
        try:
            self._queue.put_nowait(deal)
        except asyncio.QueueFull:
            logger.warning("AlertService: queue full, dropping deal")

    async def stream(self):
        """Async generator yielding SSE-formatted events."""
        while True:
            try:
                deal = await asyncio.wait_for(self._queue.get(), timeout=30)
                yield {
                    "event": "new-deal",
                    "data": json.dumps(deal, ensure_ascii=False),
                }
            except asyncio.TimeoutError:
                yield {"event": "heartbeat", "data": "{}"}
```

---

### Task 7: API Monitor Router

**Files:**
- Create: `app/routers/api_monitor.py`

- [ ] **Step 1: Create the router**

```python
# app/routers/api_monitor.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sse_starlette import EventSourceResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.watchlist import WatchlistRule
from app.models.deal_alert import DealAlert
from app.models.purchase_log import PurchaseLog

router = APIRouter()

# These will be set by main.py during startup
alert_service = None
monitor_service = None


@router.get("/monitor/stream")
async def deal_stream():
    """SSE endpoint for live deal notifications."""
    if alert_service is None:
        return JSONResponse({"error": "Alert service not initialized"}, 503)
    return EventSourceResponse(alert_service.stream())


@router.get("/watchlist")
async def list_rules(db: AsyncSession = Depends(get_db)):
    """List all watchlist rules."""
    result = await db.execute(select(WatchlistRule).order_by(desc(WatchlistRule.created_at)))
    rules = result.scalars().all()
    return [{"id": r.id, "name": r.name, "item_name": r.item_name,
             "item_type": r.item_type, "max_price": r.max_price,
             "min_discount": r.min_discount, "is_active": r.is_active,
             "notify_sound": r.notify_sound, "notify_browser": r.notify_browser,
             "auto_copy_whisper": r.auto_copy_whisper} for r in rules]


@router.post("/watchlist")
async def create_rule(rule: dict, db: AsyncSession = Depends(get_db)):
    """Create a new watchlist rule."""
    r = WatchlistRule(**rule)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    # Start monitoring if active
    if r.is_active and monitor_service:
        await monitor_service.start_rule(r)
    return {"id": r.id, "name": r.name}


@router.put("/watchlist/{rule_id}")
async def update_rule(rule_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a rule and sync monitoring state."""
    result = await db.execute(select(WatchlistRule).where(WatchlistRule.id == rule_id))
    r = result.scalar_one_or_none()
    if not r:
        return JSONResponse({"error": "Not found"}, 404)

    for key, val in data.items():
        if hasattr(r, key):
            setattr(r, key, val)
    await db.commit()
    await db.refresh(r)

    # Sync with monitor service
    if monitor_service:
        was_running = monitor_service.is_running(rule_id)
        if r.is_active and not was_running:
            await monitor_service.start_rule(r)
        elif not r.is_active and was_running:
            await monitor_service.stop_rule(rule_id)

    return {"id": r.id, "name": r.name, "is_active": r.is_active}


@router.delete("/watchlist/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a rule and stop monitoring."""
    result = await db.execute(select(WatchlistRule).where(WatchlistRule.id == rule_id))
    r = result.scalar_one_or_none()
    if not r:
        return JSONResponse({"error": "Not found"}, 404)

    if monitor_service:
        await monitor_service.stop_rule(rule_id)
    await db.delete(r)
    await db.commit()
    return {"deleted": True}


@router.get("/deals")
async def list_deals(limit: int = Query(20, le=100), db: AsyncSession = Depends(get_db)):
    """Get recent deal alerts."""
    result = await db.execute(
        select(DealAlert).order_by(desc(DealAlert.created_at)).limit(limit)
    )
    deals = result.scalars().all()
    return [{"id": d.id, "item_name": d.item_name, "price_amount": d.price_amount,
             "price_currency": d.price_currency, "market_avg": d.market_avg,
             "discount_pct": d.discount_pct, "seller_account": d.seller_account,
             "whisper_message": d.whisper_message, "trade_url": d.trade_url,
             "status": d.status} for d in deals]


@router.put("/deals/{deal_id}/mark-purchased")
async def mark_purchased(deal_id: int, data: dict = None,
                         db: AsyncSession = Depends(get_db)):
    """Mark a deal as purchased and create PurchaseLog entry."""
    result = await db.execute(select(DealAlert).where(DealAlert.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        return JSONResponse({"error": "Not found"}, 404)

    deal.status = "purchased"

    log = PurchaseLog(
        deal_alert_id=deal.id,
        item_name=deal.item_name,
        price_amount=deal.price_amount,
        price_currency=deal.price_currency,
        market_avg=deal.market_avg,
        seller_account=deal.seller_account,
        notes=(data or {}).get("notes", ""),
    )
    db.add(log)
    await db.commit()
    return {"id": deal.id, "status": "purchased"}
```

---

### Task 8: Monitor UI Template

**Files:**
- Create: `app/templates/monitor.html`

- [ ] **Step 1: Create monitor template**

```html
{% extends "base.html" %}
{% block title %}Monitor — POE2 Analytics{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="page-title">{{ _("Monitor", locale) }}</h1>
    <div class="d-flex gap-2 align-items-center">
        <span id="ws-status" class="text-muted" style="font-size:.75rem;">Connecting...</span>
        <span class="badge bg-secondary" id="deal-today">0 deals</span>
    </div>
</div>

<div class="row g-3">
    <!-- Left: Rules sidebar -->
    <div class="col-md-3">
        <div class="card" style="min-height: 300px;">
            <div class="p-3 border-bottom" style="border-color: var(--border) !important;">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="text-label">{{ _("Active Rules", locale) }}</span>
                    <button class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('rule-form').hidden = !document.getElementById('rule-form').hidden;">
                        + {{ _("New", locale) }}
                    </button>
                </div>
            </div>
            <div class="p-2" id="rules-list" style="max-height: 60vh; overflow-y: auto;">
                <div class="text-center text-muted py-4" style="font-size:.8rem;">
                    Loading rules...
                </div>
            </div>
        </div>
    </div>

    <!-- Right: Deal Feed -->
    <div class="col-md-9">
        <div class="card" style="min-height: 400px;">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center" style="border-color: var(--border) !important;">
                <span class="text-label">{{ _("Live Deal Feed", locale) }}</span>
                <span id="sse-status" class="text-muted" style="font-size:.7rem;">SSE: waiting...</span>
            </div>
            <div class="p-3" id="deal-feed" style="max-height: 70vh; overflow-y: auto;">
                <div class="text-center text-muted py-5" style="font-size:.85rem;">
                    <div style="font-size: 2rem; margin-bottom: .5rem;">📡</div>
                    {{ _("Waiting for deals...", locale) }}
                    <div style="font-size: .75rem; margin-top: .25rem;">{{ _("Create a rule to start monitoring", locale) }}</div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
// Load rules list
fetch('/api/v1/watchlist').then(r => r.json()).then(rules => {
    const el = document.getElementById('rules-list');
    if (!rules.length) {
        el.innerHTML = '<div class="text-center text-muted py-4" style="font-size:.8rem;">{{ _("No rules yet", locale) }}</div>';
        return;
    }
    el.innerHTML = rules.map(r => `
        <div class="d-flex justify-content-between align-items-center p-2 rounded mb-1"
             style="background: var(--surface); cursor: pointer; border-left: 3px solid ${r.is_active ? '#3fb950' : '#f85149'};">
            <div>
                <div style="font-size:.8rem; font-weight:600;">${r.name}</div>
                <div style="font-size:.65rem; color: var(--muted);">${r.item_name} &le; ${r.max_price || '&infin;'}c</div>
            </div>
            <span class="badge ${r.is_active ? 'bg-success' : 'bg-secondary'}" style="font-size:.6rem;">${r.is_active ? 'ON' : 'OFF'}</span>
        </div>
    `).join('');
});

// SSE connection
const sse = new EventSource('/api/v1/monitor/stream');
sse.addEventListener('new-deal', (e) => {
    const deal = JSON.parse(e.data);
    const feed = document.getElementById('deal-feed');
    const card = document.createElement('div');
    card.className = 'p-3 rounded mb-2';
    card.style.cssText = 'background:var(--surface);border:1px solid var(--purple);animation:fadeIn .3s';
    card.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <span class="badge bg-purple" style="background:var(--purple);font-size:.65rem;">${deal.discount_pct}% OFF</span>
                <strong style="font-size:.9rem;">${deal.item_name}</strong>
                <div style="font-size:.75rem;color:var(--muted);margin-top:.25rem;">
                    ${deal.price_amount} ${deal.price_currency} (market: ${deal.market_avg}) · ${deal.seller} · just now
                </div>
            </div>
            <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-secondary" style="font-size:.65rem;" onclick="copyText('${deal.whisper_message.replace(/'/g, "\\'")}')">Copy</button>
                <button class="btn btn-sm btn-outline-secondary" style="font-size:.65rem;" onclick="window.open('${deal.trade_url}')">Open</button>
                <button class="btn btn-sm btn-outline-success" style="font-size:.65rem;" onclick="markBought(${deal.id}, this)">Bought</button>
            </div>
        </div>`;
    feed.insertBefore(card, feed.firstChild);
});
sse.addEventListener('heartbeat', () => {
    document.getElementById('sse-status').textContent = 'SSE: connected';
    document.getElementById('sse-status').style.color = '#3fb950';
});
sse.onerror = () => {
    document.getElementById('sse-status').textContent = 'SSE: reconnecting...';
    document.getElementById('sse-status').style.color = '#f85149';
};

function copyText(text) { navigator.clipboard.writeText(text).then(() => {}); }
function markBought(id, btn) {
    fetch('/api/v1/deals/' + id + '/mark-purchased', {method:'PUT',headers:{'Content-Type':'application/json'},body:'{}'})
        .then(() => { btn.textContent = 'Done'; btn.disabled = true; });
}
</script>
{% endblock %}
```

---

### Task 9: Wire Everything Together

**Files:**
- Modify: `app/main.py`, `app/templates/base.html`, `app/translations.py`

- [ ] **Step 1: Initialize services in main.py lifespan**

```python
# In app/main.py, add to lifespan startup (after scheduler start):

from app.services.alert_service import AlertService
from app.services.monitor_service import MonitorService
from app.routers import api_monitor

# ... create services ...
alert_svc = AlertService()
monitor_svc = MonitorService(
    settings.GGG_POESESSID,
    "Fate of the Vaal",
    lambda item: deal_svc.evaluate(rule_id=0, rule_max_price=None,
                                   rule_min_discount=0.1, item=item)
)
api_monitor.alert_service = alert_svc
api_monitor.monitor_service = monitor_svc
```

- [ ] **Step 2: Register monitor routes in main.py**

```python
# In app/main.py:
app.include_router(api_monitor.router, prefix="/api/v1")
```

- [ ] **Step 3: Add Monitor nav link in base.html**

```html
<li class="nav-item"><a class="nav-link" href="/monitor?lang={{ locale }}">{{ _("Monitor", locale) }}</a></li>
```

- [ ] **Step 4: Add `/monitor` route to web.py**

```python
@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    return templates.TemplateResponse(request, "monitor.html", _ctx(request))
```

- [ ] **Step 5: Add translation keys**

```python
# In app/translations.py, add:
"Monitor": {"zh": "监控", "en": "Monitor"},
"Active Rules": {"zh": "活跃规则", "en": "Active Rules"},
"New": {"zh": "新建", "en": "New"},
"Live Deal Feed": {"zh": "实时交易流", "en": "Live Deal Feed"},
"Waiting for deals...": {"zh": "等待交易提醒...", "en": "Waiting for deals..."},
"Create a rule to start monitoring": {"zh": "创建规则开始监控", "en": "Create a rule to start monitoring"},
"No rules yet": {"zh": "暂无规则", "en": "No rules yet"},
```

---

### Task 10: Restart and Verify

- [ ] **Step 1: Restart server**

```bash
cd E:/project-poe2 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8006
```

- [ ] **Step 2: Verify pages**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8006/monitor
# Expected: 200

curl -s http://127.0.0.1:8006/api/v1/watchlist
# Expected: []

curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8006/api/v1/monitor/stream
# Expected: 200 (SSE stream starts)
```

- [ ] **Step 3: Create a test rule**

```bash
curl -s -X POST http://127.0.0.1:8006/api/v1/watchlist \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Rule","league_id":1,"item_name":"Chaos Orb","max_price":5.0,"min_discount":0.1,"is_active":true}'
```

- [ ] **Step 4: Verify HTML rendering**

Open `http://127.0.0.1:8006/monitor` — should show empty rules list and deal feed area.
