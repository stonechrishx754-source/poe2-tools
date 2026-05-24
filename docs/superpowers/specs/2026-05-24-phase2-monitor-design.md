# Phase 2 Design Spec: Real-Time Trade Monitor

## Scope

Add public stash data crawling and a real-time trade monitoring system
that detects underpriced items from Trade2 Live Search WebSocket and
pushes alerts to the browser via SSE. No ladder functionality.

## Decisions

| Topic | Choice |
|-------|--------|
| Monitoring mode | Preset rules + ad-hoc search tracking |
| Notification | Browser only (page notification + sound) |
| Navigation | Dedicated "Monitor" tab in existing navbar |
| Layout | Left-Right: rules sidebar + live deal feed |
| POESESSID | User enters via UI, stored in .env |
| Compliance | Copy whisper / open trade page — no auto-buy |

## Architecture

```
watchlist rules (DB) ──→ MonitorService ──→ ggg_trade2_ws.py ──WS──→ GGG Trade2
                               │
                         DealService (discount calc)
                               │
                         AlertService ──SSE──→ Browser (/api/v1/monitor/stream)
                               │
                         deal_alerts (DB) ──→ monitor.html (HTMX)
```

### Two modes, one pipeline

1. **Preset Rules**: user creates a watchlist rule (item name, max price, min discount).
   MonitorService opens one Trade2 WS per rule. New items feed into DealService.

2. **Search & Track**: user searches via /trades page, gets results, clicks "Track this search".
   Creates a temporary rule, monitors until user stops it.

3. **Deal pipeline**: WS push → extract price → compare market avg (from price_history table / poe2scout)
   → if discount >= threshold → insert deal_alert → SSE broadcast

## Data Models

### stash_tabs
- stash_id (unique), league_id, account_name, stash_type, items_count, snapshot_at
  Stores only summaries; individual priced items go to stash_items.

### watchlist_rules
- name, league_id, item_name (fuzzy match), item_type, max_price (chaos),
  min_discount (0.0–1.0), is_active, notify_sound, notify_browser,
  auto_copy_whisper, created_at, updated_at

### deal_alerts
- rule_id, trade2_id, item_name+item_type, item_json (full item data),
  seller_account/character, stash_tab, price_amount+currency,
  market_avg, discount_pct, whisper_message, trade_url,
  status (new/notified/clicked/purchased/expired), timestamps

### purchase_log
- deal_alert_id, item_name, price_amount+currency, market_avg, discount_pct,
  seller_account, purchased_at, notes

## Core Components

### ggg_trade2_ws.py (crawler)
- WebSocket client for GGG Trade2 Live Search
- Connects to: `wss://pathofexile.com/api/trade2/live/poe2/{league}/{queryId}`
- Requires POESESSID cookie, Origin header
- On "new" message → fetch item details → callback
- Handles: reconnect on disconnect, rate limit headers, heartbeat

### monitor_service.py (service)
- Manages WS connections per active watchlist rule
- Start/stop individual rules on demand
- Route new items to DealService
- Enforce GGG rate limits (max ~20 concurrent connections)

### deal_service.py (service)
- Extract price from listing data
- Compute market average from price_history table
- discount_pct = (market_avg - item_price) / market_avg
- If discount_pct >= rule.min_discount → create deal_alert
- Populate whisper message from item JSON

### alert_service.py (service)
- asyncio.Queue-based event bus
- SSE endpoint pushes deal events to connected browsers
- Each deal has: item_name, price, market_avg, discount_pct, seller, whisper, trade_url

### api_monitor.py (router)
- `GET /api/v1/monitor/stream` — SSE endpoint (EventSourceResponse)
- `GET /api/v1/watchlist` — list rules
- `POST /api/v1/watchlist` — create rule
- `PUT /api/v1/watchlist/{id}` — update rule
- `DELETE /api/v1/watchlist/{id}` — delete rule
- `POST /api/v1/watchlist/{id}/start` / `/stop` — toggle rule
- `GET /api/v1/deals` — recent deals (paginated)
- `PUT /api/v1/deals/{id}/mark-purchased` — mark as bought

### ggg_stash.py (crawler)
- Poll GGG Public Stash API with next_change_id cursor
- Extract items with "note" field (priced items) → stash_items
- Store stash summary → stash_tabs
- Run every 5 minutes (configurable)

## UI Pages

### /monitor — Monitor Dashboard
- **Left sidebar (280px)**: list of active rules with status indicators
  - Each rule: name, item, max price, time active, hits count, on/off toggle
  - "+ New Rule" button → opens rule form (inline modal)
- **Right content**: live deal feed (SSE-driven)
  - New deals appear at top with animation
  - Deal card: item icon, name, discount badge, price vs market avg, seller, time
  - Actions: [Copy Whisper] [Open Trade Page] [Mark Purchased]
  - Old deals fade and move down
- **Top stats bar**: active rules count, today's deals, connection status indicator

### /watchlist — Rule Management
- Create/Edit rule form
- Table of all rules with toggle, stats, delete

### /trades — Trade Search (extend existing)
- Add "Track This Search" button to search results
- Creates a monitor rule from search parameters

## Error Handling

- WS disconnect → auto-reconnect with exponential backoff (cap 60s)
- POESESSID missing/invalid → show clear error on monitor page
- Rate limit exceeded → pause new rule creation, show warning
- Deal detection with no market data → skip, don't crash
- SSE connection lost → client auto-reconnects (native EventSource behavior)

## Rate Limit Strategy

Trade2 Live Search limits (account-level, with POESESSID):
- ~50 live-search actions per rolling 24h
- Max ~20 concurrent WS connections

Strategy: establish WS once per rule, keep alive. Don't tear down/recreate.
When user stops a rule, gracefully close but don't immediately reuse the slot.
First-come-first-served for the 20 connection slots.

## File Changes

### New files (11)
- `app/models/stash.py`
- `app/models/watchlist.py`
- `app/models/deal_alert.py`
- `app/models/purchase_log.py`
- `app/crawlers/ggg_stash.py`
- `app/crawlers/ggg_trade2_ws.py`
- `app/services/monitor_service.py`
- `app/services/deal_service.py`
- `app/services/alert_service.py`
- `app/routers/api_monitor.py`
- `app/templates/monitor.html`

### Modified files
- `app/models/__init__.py` — add new models
- `app/routers/web.py` — add /monitor route
- `app/scheduler.py` — add ggg_stash crawl job
- `app/templates/base.html` — add Monitor nav link
- `app/templates/items.html` — add category tabs for stash data
- `app/translations.py` — add monitor-related keys

## Verification

1. Start app, navigate to /monitor
2. Create a watchlist rule (e.g., "Chaos Orb ≤ 3.0")
3. Verify WS connection indicator shows green
4. Wait for deal detection (or simulate with mock data)
5. Verify SSE pushes deal card to feed
6. Click Copy Whisper → clipboard contains whisper message
7. Click Open Trade Page → new tab opens to trade site
8. Click Mark Purchased → status updates in DB
9. Toggle rule off → WS disconnects, feed stops for that rule
10. Verify stash data flowing from GGG API (check dashboard stats increase)
