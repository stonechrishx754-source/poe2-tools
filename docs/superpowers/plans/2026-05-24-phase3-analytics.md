# Phase 3: Trade Search + Analytics + Purchase Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trade search page, dashboard top movers, purchase history with ROI, deal detail, and data compaction.

**Architecture:** One new crawler (GggTrade2Crawler via BaseCrawler), one new service (AnalysisService), three new templates (trades.html, purchases.html, deal detail fragment), and modifications to existing routes/templates for nav, dashboard analytics, and scheduler maintenance.

**Tech Stack:** Python FastAPI, SQLAlchemy 2.0 + aiosqlite, Jinja2/HTMX, Chart.js, BaseCrawler pattern

**Spec:** `docs/superpowers/specs/2026-05-24-phase3-analytics.md`

---

## File Map

### Create (4)
| File | Responsibility |
|------|---------------|
| `app/crawlers/ggg_trade2.py` | GGG Trade2 Search API crawler |
| `app/services/analysis_service.py` | Top movers computation from item_snapshots |
| `app/templates/trades.html` | Search form + HTMX result table + Track button |
| `app/templates/purchases.html` | Purchase history + ROI summary cards |

### Modify (5)
| File | Change |
|------|--------|
| `app/routers/web.py` | Add `/trades`, `/purchases` routes |
| `app/templates/base.html` | Add Trades nav link |
| `app/translations.py` | Add Phase 3 translation keys |
| `app/routers/api_dashboard.py` | Extend summary with top_gainers/top_losers |
| `app/templates/index.html` | Add gainers/losers card columns |
| `app/routers/api_monitor.py` | Add `/deals/{id}/detail` endpoint |
| `app/templates/monitor.html` | Add click-to-expand on deal cards |
| `app/scheduler.py` | Add `compact_price_history` cron job |

---

### Task 1: GGG Trade2 Search Crawler (3.1)

**Files:** Create `app/crawlers/ggg_trade2.py`

- [ ] **Step 1: Create the crawler**

```python
import hashlib
import json
import logging
import time
from typing import Any

from app.config import settings
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

TRADE2_SEARCH = "https://www.pathofexile.com/api/trade2/search/poe2"
CACHE_TTL = 30  # seconds


class GggTrade2Crawler(BaseCrawler):
    """Searches GGG Trade2 for items. Caches results for 30s to respect rate limits."""

    source_name = "ggg_trade2"
    rate_limit_per_second = 0.33  # 1 req per 3s
    burst_size = 1

    def __init__(self, poesessid: str = ""):
        super().__init__()
        self._poesessid = poesessid or settings.GGG_POESESSID or ""
        self._cache: dict[str, tuple[float, dict]] = {}

    async def search(self, league: str, name: str = "", item_type: str = "",
                     max_price: float | None = None) -> dict[str, Any]:
        """Search Trade2 and return listing results.

        Returns: {"result": [...], "total": N, "id": "query_id"}
        On error or no POESESSID: {"error": "message"}
        """
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
```

- [ ] **Step 2: Update BaseCrawler to support POST**

Read `app/crawlers/base.py`. Add a `method` and `json_body` parameter to the `fetch` method. If the file already has these parameters, skip. If not, add them:

```python
async def fetch(self, url: str, method: str = "GET", json_body: dict = None,
                extra_headers: dict = None, **kwargs) -> Any:
```

In the method body, use `self.client.post(url, json=json_body)` when `method == "POST"`, otherwise use `self.client.get(url)`.

- [ ] **Step 3: Verify import**

```bash
cd E:/project-poe2 && python -c "from app.crawlers.ggg_trade2 import GggTrade2Crawler; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/crawlers/ggg_trade2.py app/crawlers/base.py
git commit -m "feat: add GggTrade2Crawler for Trade2 search API"
```

---

### Task 2: Trade Search Page (3.1 + 3.2)

**Files:** Create `app/templates/trades.html`, Modify `app/routers/web.py`, `app/templates/base.html`, `app/translations.py`

- [ ] **Step 1: Add trade search HTML route**

In `app/routers/web.py`, add after the /monitor route:

```python
@router.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    return templates.TemplateResponse(request, "trades.html", _ctx(request))
```

- [ ] **Step 2: Add API search endpoint to web.py**

In `app/routers/web.py`, add after the existing fragment routes:

```python
@router.get("/api/v1/trade/search", response_class=HTMLResponse)
async def trade_search_fragment(
    request: Request,
    name: str = Query(""),
    item_type: str = Query(""),
    max_price: float | None = Query(None),
):
    """HTMX fragment: search Trade2 and return results."""
    from app.crawlers.ggg_trade2 import GggTrade2Crawler

    league = _active_league(request)
    crawler = GggTrade2Crawler()
    result = await crawler.search(league, name=name, item_type=item_type, max_price=max_price)
    await crawler.close()

    if "error" in result:
        return HTMLResponse(
            f'<div class="text-center text-muted py-4">{result["error"]}</div>'
        )

    items = result.get("result", [])
    if not items:
        return HTMLResponse(
            '<div class="text-center text-muted py-4">No items found</div>'
        )

    # Fetch item details (up to 10)
    query_id = result.get("id", "")
    from app.crawlers.ggg_trade2_ws import TRADE2_FETCH
    import httpx
    ids = ",".join(items[:10])
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{TRADE2_FETCH}/{ids}?query={query_id}",
            cookies={"POESESSID": settings.GGG_POESESSID},
        )
        details = r.json().get("result", [])

    # Render results
    rows_html = ""
    for item in details:
        listing = item.get("listing", {})
        item_data = item.get("item", {})
        price = listing.get("price", {})
        p_amount = price.get("amount", "?")
        p_currency = price.get("currency", "?")
        i_name = item_data.get("name") or item_data.get("typeLine", "?")
        i_type = item_data.get("typeLine", "")
        seller = listing.get("account", {}).get("lastCharacterName", "?")
        icon = item_data.get("icon", "")
        trade_id = item.get("id", "")

        rows_html += f"""
        <tr>
            <td style="width:40px">{'<img src="'+icon+'" style="width:32px;height:32px">' if icon else ''}</td>
            <td>{i_name}</td>
            <td><span class="badge bg-secondary" style="font-size:.65rem;">{i_type}</span></td>
            <td class="text-end">{p_amount} {p_currency}</td>
            <td class="text-end">{seller}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" style="font-size:.65rem;"
                        onclick="trackItem('{i_name}', '{i_type}', {p_amount})">Track</button>
            </td>
        </tr>"""

    return HTMLResponse(f"""
    <div class="text-muted small mb-2">Found {result.get('total', 0)} items</div>
    <table class="table table-dark table-sm">
        <thead><tr><th></th><th>Name</th><th>Type</th><th class="text-end">Price</th><th class="text-end">Seller</th><th></th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """)
```

- [ ] **Step 3: Create trades.html**

```html
{% extends "base.html" %}
{% block title %}{{ _("Trades", locale) }} — POE2 Analytics{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="page-title">{{ _("Trades", locale) }}</h1>
</div>

<div class="card p-3 mb-3">
    <div class="row g-2">
        <div class="col-md-4">
            <input class="form-control form-control-dark form-control-sm" id="search-name"
                   placeholder="{{ _('Item name', locale) }}" value="">
        </div>
        <div class="col-md-3">
            <input class="form-control form-control-dark form-control-sm" id="search-type"
                   placeholder="{{ _('Type (optional)', locale) }}">
        </div>
        <div class="col-md-2">
            <input class="form-control form-control-dark form-control-sm" id="search-price"
                   type="number" placeholder="{{ _('Max price', locale) }}">
        </div>
        <div class="col-md-2">
            <button class="btn btn-sm btn-outline-info w-100"
                    hx-get="/api/v1/trade/search"
                    hx-include="#search-name,#search-type,#search-price"
                    hx-target="#search-results"
                    hx-indicator="#search-spinner">
                {{ _("Search", locale) }}
            </button>
        </div>
    </div>
</div>

<div id="search-spinner" class="htmx-indicator text-center py-3">
    <div class="spinner-border spinner-border-sm text-muted" role="status"></div>
</div>

<div id="search-results" class="table-responsive">
    <div class="text-center text-muted py-5">
        {{ _("Search for items to find deals", locale) }}
    </div>
</div>

<!-- Hidden track modal (reuses monitor create API) -->
<script>
function trackItem(name, type, price) {
    const data = {
        name: 'Track ' + name,
        item_name: name,
        item_type: type || '',
        max_price: price || 0,
        min_discount: 0.1,
        is_active: true,
        notify_sound: true,
        notify_browser: true,
        auto_copy_whisper: false,
        league_id: 1,
    };
    fetch('/api/v1/watchlist', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
        .then(r => r.json()).then(d => {
            alert('Rule created: ' + d.name + ' (id=' + d.id + ')');
        });
}
</script>
{% endblock %}
```

- [ ] **Step 4: Add nav link and translations**

In `app/templates/base.html`, add before the Monitor link:
```html
<li class="nav-item"><a class="nav-link" href="/trades?lang={{ locale }}">{{ _("Trades", locale) }}</a></li>
```

In `app/translations.py`, add inside TRANSLATIONS dict:
```python
"Trades": {"zh": "交易", "en": "Trades"},
"Search for items to find deals": {"zh": "搜索物品以发现交易机会", "en": "Search for items to find deals"},
"Track": {"zh": "监控", "en": "Track"},
"Item name": {"zh": "物品名称", "en": "Item name"},
"Type (optional)": {"zh": "类型（可选）", "en": "Type (optional)"},
"Max price": {"zh": "最高价格", "en": "Max price"},
```

- [ ] **Step 5: Verify**

```bash
cd E:/project-poe2 && python -c "from app.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add app/templates/trades.html app/routers/web.py app/templates/base.html app/translations.py
git commit -m "feat: add trade search page with one-click watchlist creation"
```

---

### Task 3: Analysis Service (3.3)

**Files:** Create `app/services/analysis_service.py`

- [ ] **Step 1: Create the service**

```python
"""Market analysis: top movers, trends from item_snapshots."""
import logging
from sqlalchemy import func, select, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.item import ItemSnapshot

logger = logging.getLogger(__name__)


async def get_top_movers(
    db: AsyncSession,
    league_id: int,
    direction: str = "gainers",
    top_n: int = 5,
) -> list[dict]:
    """Compute top price gainers or losers over the last 24 hours.

    Compares the average chaos_value from 24-48h ago against the most
    recent 24h window, returning items with the biggest % change.
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    two_days_ago = now - timedelta(hours=48)

    # Recent avg (last 24h)
    recent = (
        select(
            ItemSnapshot.item_name,
            func.avg(ItemSnapshot.chaos_value).label("recent_avg"),
            func.max(ItemSnapshot.icon_url).label("icon_url"),
        )
        .where(
            ItemSnapshot.league_id == league_id,
            ItemSnapshot.snapshot_at >= day_ago,
            ItemSnapshot.chaos_value.isnot(None),
        )
        .group_by(ItemSnapshot.item_name)
    ).subquery()

    # Previous avg (24-48h ago)
    previous = (
        select(
            ItemSnapshot.item_name,
            func.avg(ItemSnapshot.chaos_value).label("prev_avg"),
        )
        .where(
            ItemSnapshot.league_id == league_id,
            ItemSnapshot.snapshot_at.between(two_days_ago, day_ago),
            ItemSnapshot.chaos_value.isnot(None),
        )
        .group_by(ItemSnapshot.item_name)
    ).subquery()

    change_pct = (
        (recent.c.recent_avg - previous.c.prev_avg) / previous.c.prev_avg * 100
    ).label("change_pct")

    query = (
        select(
            recent.c.item_name,
            recent.c.recent_avg,
            previous.c.prev_avg,
            recent.c.icon_url,
            change_pct,
        )
        .join(previous, recent.c.item_name == previous.c.item_name)
        .where(previous.c.prev_avg > 0)
        .order_by(change_pct.desc() if direction == "gainers" else change_pct.asc())
        .limit(top_n)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "item_name": r.item_name,
            "recent_avg": round(r.recent_avg, 2),
            "prev_avg": round(r.prev_avg, 2),
            "change_pct": round(r.change_pct, 1),
            "icon_url": r.icon_url,
        }
        for r in rows
    ]
```

- [ ] **Step 2: Verify import**

```bash
cd E:/project-poe2 && python -c "from app.services.analysis_service import get_top_movers; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/services/analysis_service.py
git commit -m "feat: add AnalysisService for 24h top movers computation"
```

---

### Task 4: Dashboard Enhancement (3.4)

**Files:** Modify `app/routers/api_dashboard.py`, `app/templates/index.html`, `app/translations.py`

- [ ] **Step 1: Extend dashboard summary API**

In `app/routers/api_dashboard.py`, in the `dashboard_summary` function, add before the return:

```python
from app.services.analysis_service import get_top_movers

gainers = await get_top_movers(db, league_obj.id, "gainers", 5)
losers = await get_top_movers(db, league_obj.id, "losers", 5)
```

And update the return to include them:
```python
return DashboardSummary(
    total_currencies=currency_count or 0,
    total_items=item_count or 0,
    total_gems=gem_count or 0,
    last_crawl=last_crawl.started_at.isoformat() if last_crawl else None,
    active_league=league,
    top_gainers=gainers,
    top_losers=losers,
)
```

Update the Pydantic schema `DashboardSummary` in `app/schemas/dashboard.py`:
```python
from pydantic import BaseModel, Field

class MoverItem(BaseModel):
    item_name: str = ""
    recent_avg: float = 0
    prev_avg: float = 0
    change_pct: float = 0
    icon_url: str | None = None

class DashboardSummary(BaseModel):
    total_currencies: int = 0
    total_items: int = 0
    total_gems: int = 0
    last_crawl: str | None = None
    active_league: str = ""
    top_gainers: list[MoverItem] = Field(default_factory=list)
    top_losers: list[MoverItem] = Field(default_factory=list)
```

- [ ] **Step 2: Add gainers/losers to index.html**

In `app/templates/index.html`, add after the Quick Nav row, before `{% endblock %}`:

```html
<!-- Top Movers -->
{% if top_gainers or top_losers %}
<div class="row g-3 mb-4">
    <div class="col-md-6">
        <div class="card p-3">
            <h6 class="section-title mb-3" style="color: #3fb950;">{{ _("Top Gainers 24h", locale) }}</h6>
            {% for item in top_gainers %}
            <div class="d-flex align-items-center gap-2 mb-2">
                {% if item.icon_url %}
                <img src="{{ item.icon_url }}" style="width:24px;height:24px;">
                {% endif %}
                <span class="flex-grow-1" style="font-size:.85rem;">{{ item.item_name }}</span>
                <span class="badge bg-success" style="font-size:.7rem;">+{{ item.change_pct }}%</span>
            </div>
            {% endfor %}
        </div>
    </div>
    <div class="col-md-6">
        <div class="card p-3">
            <h6 class="section-title mb-3" style="color: #f85149;">{{ _("Top Losers 24h", locale) }}</h6>
            {% for item in top_losers %}
            <div class="d-flex align-items-center gap-2 mb-2">
                {% if item.icon_url %}
                <img src="{{ item.icon_url }}" style="width:24px;height:24px;">
                {% endif %}
                <span class="flex-grow-1" style="font-size:.85rem;">{{ item.item_name }}</span>
                <span class="badge bg-danger" style="font-size:.7rem;">{{ item.change_pct }}%</span>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endif %}
```

Update the index route in `web.py` to pass the movers data:

```python
from app.services.analysis_service import get_top_movers

# In the index() function, add before return:
gainers = await get_top_movers(db, league_obj.id, "gainers", 5)
losers = await get_top_movers(db, league_obj.id, "losers", 5)

return templates.TemplateResponse(
    request, "index.html",
    _ctx(request, league=league, last_crawl=last_crawl, total_entries=total_entries,
         top_gainers=gainers, top_losers=losers),
)
```

- [ ] **Step 3: Add translations**

```python
"Top Gainers 24h": {"zh": "24h 涨幅榜", "en": "Top Gainers 24h"},
"Top Losers 24h": {"zh": "24h 跌幅榜", "en": "Top Losers 24h"},
```

- [ ] **Step 4: Verify**

```bash
cd E:/project-poe2 && python -c "from app.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/routers/api_dashboard.py app/schemas/dashboard.py app/templates/index.html app/routers/web.py app/translations.py
git commit -m "feat: add 24h top gainers/losers to dashboard"
```

---

### Task 5: Purchase History Page (3.5)

**Files:** Create `app/templates/purchases.html`, Modify `app/routers/web.py`, `app/translations.py`

- [ ] **Step 1: Add route**

In `app/routers/web.py`:

```python
@router.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request, db: AsyncSession = Depends(get_db)):
    from app.models.purchase_log import PurchaseLog
    from sqlalchemy import func

    result = await db.execute(
        select(PurchaseLog).order_by(desc(PurchaseLog.purchased_at))
    )
    purchases = result.scalars().all()

    total_spent = sum(p.price_amount for p in purchases)
    total_saved = sum((p.market_avg or p.price_amount) - p.price_amount for p in purchases)
    roi = (total_saved / total_spent * 100) if total_spent > 0 else 0

    return templates.TemplateResponse(
        request, "purchases.html",
        _ctx(request, league=league,
             purchases=purchases, total_spent=round(total_spent, 0),
             total_saved=round(total_saved, 0), roi=round(roi, 1),
             count=len(purchases)),
    )
```

- [ ] **Step 2: Create purchases.html**

```html
{% extends "base.html" %}
{% block title %}{{ _("Purchases", locale) }} — POE2 Analytics{% endblock %}

{% block content %}
<h1 class="page-title mb-4">{{ _("Purchases", locale) }}</h1>

<div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
        <div class="card-stat">
            <div class="value">{{ count }}</div>
            <div class="label">{{ _("Total Purchases", locale) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="card-stat">
            <div class="value text-chaos">{{ total_spent }}</div>
            <div class="label">{{ _("Total Spent", locale) }} (chaos)</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="card-stat">
            <div class="value" style="color:#3fb950;">{{ total_saved }}</div>
            <div class="label">{{ _("Total Saved", locale) }} (chaos)</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="card-stat">
            <div class="value" style="color:{{ '#3fb950' if roi > 0 else '#f85149' }};">{{ roi }}%</div>
            <div class="label">{{ _("ROI", locale) }}</div>
        </div>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-dark">
        <thead><tr>
            <th>{{ _("Date", locale) }}</th><th>{{ _("Item", locale) }}</th>
            <th class="text-end">{{ _("Price", locale) }}</th>
            <th class="text-end">{{ _("Market", locale) }}</th>
            <th class="text-end">{{ _("Saved", locale) }}</th>
            <th>{{ _("Seller", locale) }}</th>
        </tr></thead>
        <tbody>
        {% for p in purchases %}
        <tr>
            <td style="font-size:.8rem;">{{ p.purchased_at.strftime('%m-%d %H:%M') }}</td>
            <td>{{ p.item_name }}</td>
            <td class="text-end">{{ p.price_amount }} {{ p.price_currency }}</td>
            <td class="text-end">{{ "%.0f"|format(p.market_avg) if p.market_avg else '—' }}</td>
            <td class="text-end" style="color:{{ '#3fb950' if (p.market_avg or 0) - p.price_amount > 0 else '#f85149' }};">
                {{ "%.0f"|format((p.market_avg or 0) - p.price_amount) if p.market_avg else '—' }}
            </td>
            <td>{{ p.seller_account or '—' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="6" class="text-center text-muted py-4">{{ _("No purchases yet", locale) }}</td></tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

- [ ] **Step 3: Add translations and nav link**

In `app/templates/base.html`, add after Trades link:
```html
<li class="nav-item"><a class="nav-link" href="/purchases?lang={{ locale }}">{{ _("Purchases", locale) }}</a></li>
```

In `app/translations.py`:
```python
"Purchases": {"zh": "购买记录", "en": "Purchases"},
"Total Purchases": {"zh": "总购买次数", "en": "Total Purchases"},
"Total Spent": {"zh": "总花费", "en": "Total Spent"},
"Total Saved": {"zh": "总节省", "en": "Total Saved"},
"ROI": {"zh": "投资回报率", "en": "ROI"},
"Date": {"zh": "日期", "en": "Date"},
"Item": {"zh": "物品", "en": "Item"},
"Market": {"zh": "市价", "en": "Market"},
"Saved": {"zh": "节省", "en": "Saved"},
"Seller": {"zh": "卖家", "en": "Seller"},
"No purchases yet": {"zh": "暂无购买记录", "en": "No purchases yet"},
```

- [ ] **Step 4: Verify**

```bash
cd E:/project-poe2 && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/purchases.html app/routers/web.py app/translations.py app/templates/base.html
git commit -m "feat: add purchase history page with ROI statistics"
```

---

### Task 6: Deal Detail Enhancement (3.6)

**Files:** Modify `app/routers/api_monitor.py`, `app/templates/monitor.html`

- [ ] **Step 1: Add deal detail API endpoint**

In `app/routers/api_monitor.py`, add:

```python
@router.get("/deals/{deal_id}/detail")
async def deal_detail(deal_id: int, db: AsyncSession = Depends(get_db)):
    """Get deal detail with price history and similar items."""
    result = await db.execute(
        select(DealAlert).where(DealAlert.id == deal_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        return JSONResponse({"error": "Not found"}, 404)

    # Price history (last 7 days)
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    history_result = await db.execute(
        select(ItemSnapshot)
        .where(
            ItemSnapshot.item_name == deal.item_name,
            ItemSnapshot.snapshot_at >= cutoff,
        )
        .order_by(ItemSnapshot.snapshot_at.asc())
    )
    history = [
        {"snapshot_at": h.snapshot_at.isoformat(), "chaos_value": h.chaos_value}
        for h in history_result.scalars().all()
    ]

    # Similar items (cheapest current listings for same item name)
    from app.services.item_service import get_latest_items
    league_id = 1  # default
    similar = [i for i in await get_latest_items(db, league_id, limit=10)
               if i["name"] == deal.item_name][:5]

    return {
        "deal": {
            "id": deal.id, "item_name": deal.item_name,
            "price_amount": deal.price_amount, "price_currency": deal.price_currency,
            "market_avg": deal.market_avg, "discount_pct": deal.discount_pct,
            "seller_account": deal.seller_account,
        },
        "history": history,
        "similar": similar,
    }
```

- [ ] **Step 2: Update monitor.html to show detail panel**

In `app/templates/monitor.html`, replace the static deal card with a click-expand version. Change the `card.innerHTML` to include a click handler that loads detail:

Add to the card click logic after inserting the card:
```javascript
card.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON') return;
    fetch('/api/v1/deals/' + deal.id + '/detail')
        .then(r => r.json()).then(d => showDealDetail(d));
});
```

And add the `showDealDetail` function:
```javascript
function showDealDetail(d) {
    const panel = document.createElement('div');
    panel.className = 'card p-3 mt-2';
    panel.style.cssText = 'background:var(--surface);';
    let historyLabels = d.history.map(h => new Date(h.snapshot_at).toLocaleDateString());
    let historyData = d.history.map(h => h.chaos_value);
    let similarHtml = d.similar.map(s =>
        '<div class="d-flex justify-content-between" style="font-size:.8rem;"><span>'+s.name+'</span><span>'+s.chaos_value+'c</span></div>'
    ).join('');
    panel.innerHTML = `
        <div class="d-flex justify-content-between mb-2">
            <strong>${d.deal.item_name}</strong>
            <button class="btn btn-sm btn-outline-secondary" onclick="this.parentElement.parentElement.remove()">x</button>
        </div>
        <canvas id="detail-chart-${d.deal.id}" height="60"></canvas>
        <div class="mt-2"><small class="text-muted">Current cheapest:</small>${similarHtml}</div>
    `;
    document.getElementById('deal-feed').insertBefore(panel, document.querySelector('.p-3.rounded.mb-2'));
    // Render chart
    setTimeout(() => {
        new Chart(document.getElementById('detail-chart-'+d.deal.id), {
            type:'line', data:{labels:historyLabels,datasets:[{data:historyData,borderColor:'#58a6ff',fill:false,pointRadius:0}]},
            options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{display:false},y:{grid:{color:'rgba(255,255,255,.03)'}}}}
        });
    }, 100);
}
```

- [ ] **Step 3: Verify**

```bash
cd E:/project-poe2 && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/routers/api_monitor.py app/templates/monitor.html
git commit -m "feat: add deal detail panel with price chart and similar items"
```

---

### Task 7: Data Compaction (3.7)

**Files:** Modify `app/scheduler.py`

- [ ] **Step 1: Add compaction job**

In `app/scheduler.py`, add the function:

```python
async def compact_price_history():
    """Daily: aggregate item_snapshots into price_history, prune old data."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete

    threshold = datetime.now(timezone.utc) - timedelta(days=30)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    async with AsyncSessionLocal() as db:
        # Aggregate yesterday's snapshots into price_history
        yesterday = today - timedelta(days=1)
        result = await db.execute(
            select(
                ItemSnapshot.item_name,
                ItemSnapshot.league_id,
                func.avg(ItemSnapshot.chaos_value).label("avg_val"),
                func.min(ItemSnapshot.chaos_value).label("min_val"),
                func.max(ItemSnapshot.chaos_value).label("max_val"),
                func.count(ItemSnapshot.id).label("sample_size"),
            )
            .where(
                ItemSnapshot.snapshot_at >= yesterday,
                ItemSnapshot.snapshot_at < today,
                ItemSnapshot.chaos_value.isnot(None),
            )
            .group_by(ItemSnapshot.item_name, ItemSnapshot.league_id)
        )
        rows = result.all()

        from app.models.price_history import PriceHistory
        compacted = 0
        for r in rows:
            ph = PriceHistory(
                league_id=r.league_id,
                entity_type="item",
                entity_name=r.item_name,
                price_chaos=round(r.avg_val, 2),
                sample_size=r.sample_size,
                recorded_at=today,
            )
            db.add(ph)
            compacted += 1

        # Delete snapshots older than 30 days
        del_result = await db.execute(
            delete(ItemSnapshot).where(ItemSnapshot.snapshot_at < threshold)
        )
        deleted = del_result.rowcount

        await db.commit()
        logger.info("Compaction: %d price_history rows, %d old snapshots deleted", compacted, deleted)
```

In `start_scheduler()`, add:
```python
scheduler.add_job(
    compact_price_history,
    "cron", hour=3, minute=0,
    id="price_compaction",
    max_instances=1, replace_existing=True,
)
```

- [ ] **Step 2: Verify**

```bash
cd E:/project-poe2 && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/scheduler.py
git commit -m "feat: add daily price history compaction and 30-day snapshot cleanup"
```

---

### Task 8: Integration Verification

- [ ] **Step 1: Restart server**

```bash
taskkill //F //PID $(netstat -ano | grep ":8006" | grep LISTEN | awk '{print $NF}') 2>/dev/null
sleep 2 && cd E:/project-poe2 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8006 &
sleep 5
```

- [ ] **Step 2: Verify all pages**

```bash
for url in "/" "/currency" "/items" "/gems" "/trades" "/monitor" "/purchases"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8006${url}")
    echo "  $code $url"
done
```
Expected: All 200

- [ ] **Step 3: Verify new APIs**

```bash
curl -s http://127.0.0.1:8006/api/v1/dashboard/summary | python -c "import sys,json; d=json.load(sys.stdin); print('gainers:', len(d.get('top_gainers',[])), 'losers:', len(d.get('top_losers',[])))"
```
Expected: `gainers: 5 losers: 5` (or fewer if not enough data)

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8006/api/v1/trade/search
```
Expected: `200` (or error with POESESSID message)

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8006/api/v1/purchases
```
Note: This endpoint `/api/v1/purchases` may need to be added to api_monitor or web.py. If the purchases page reads from the DB directly via the web route, skip this.

- [ ] **Step 4: Commit final verification**

```bash
git add -A
git commit -m "chore: Phase 3 integration verification"
```
