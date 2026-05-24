# Phase 3 Design Spec: Trade Search + Analytics + Purchase Tracking

## Scope

Add trade search page, dashboard analytics (top movers), purchase history with ROI stats,
deal detail enrichment, and daily data compaction. 4 new files, 5 modifications.

## Feature: Trade Search Page (3.1 + 3.2)

### Flow
User types item name/type/price cap → GGG Trade2 Search API → table of online listings →
"Track" button on each row → pre-fills watchlist form → creates rule.

### New files
- `app/crawlers/ggg_trade2.py` — `GggTrade2Crawler(BaseCrawler)`, single method `search(league, query)`
  POSTs to `/api/trade2/search/poe2/{league}`, returns `{id, result: [...], total}`.
  Cache: in-memory dict, 30s TTL per search params hash. Requires POESESSID.
  Rate limited: 1 req/3s (conservative for the ~5/12s actual limit).
- `app/templates/trades.html` — search form (item name, type dropdown, max price) +
  HTMX result table. Each row: icon, name, type, price, seller, online status, "Track" button.
  "Track" opens a mini modal with pre-filled watchlist form (name=item name, item_name=item name, max_price=item price).

### Modified files
- `app/routers/web.py` — add `GET /trades` route
- `app/templates/base.html` — add nav link (after Gems, before Monitor)
- `app/translations.py` — add keys: Trades, Search, Track, etc.

### API endpoints
- `GET /api/v1/trade/search?league=...&name=...&type=...&max_price=...` — returns Trade2 results

### Error handling
- No POESESSID → show "Set POESESSID in .env to search" on page
- Rate limited → show "Search cooldown, try again in N seconds"
- No results → show "No items found" empty state

## Feature: Dashboard Top Movers (3.3 + 3.4)

### Data source
Existing `item_snapshots` table. Compare avg price in last 24h window vs prior 24h window.

### New files
- `app/services/analysis_service.py` — `get_top_movers(db, league_id, direction, top_n=5)`
  direction: "gainers" or "losers". Pure SQL with window functions.
  Returns `[{item_name, current_avg, previous_avg, change_pct, icon_url}]`

### Modified files
- `app/routers/api_dashboard.py` — extend `/dashboard/summary` response with `top_gainers` and `top_losers` arrays
- `app/templates/index.html` — add two card columns below existing Quick Nav:
  - Left: "Top Gainers 24h" — green text, up arrow, items sorted by % gain
  - Right: "Top Losers 24h" — red text, down arrow, items sorted by % drop
  Each: item icon + name + change_pct badge
- `app/translations.py` — add keys: Top Gainers, Top Losers, 24h Change

## Feature: Purchase Tracking (3.5)

### Data source
Existing `purchase_log` table (created by Phase 2 mark-purchased endpoint).

### New files
- `app/templates/purchases.html` — summary cards (total purchases, total spent, total saved, avg ROI) +
  table of all purchases (date, item, price paid, market price, discount %, seller)

### Modified files
- `app/routers/web.py` — add `GET /purchases` route
- `app/translations.py` — add keys: Purchases, Total Spent, Total Saved, ROI etc.

### API endpoints
- `GET /api/v1/purchases` — returns all PurchaseLog rows with computed discount_pct

## Feature: Deal Detail Enhancement (3.6)

### Flow
Click a deal card in /monitor → expands inline or opens a detail panel showing:
- Price history chart (7 days, from ItemSnapshot)
- Top 5 current cheapest listings for same item (from latest ItemSnapshot)

### Modified files
- `app/routers/api_monitor.py` — add `GET /api/v1/deals/{id}/detail` returning JSON with history + similar items
- `app/templates/monitor.html` — add click handler on deal cards that fetches detail and renders chart + similar items panel
- `app/templates/fragments/price_chart.html` — reuse existing chart fragment

## Feature: Data Compaction (3.7)

### Logic
Daily cron at 03:00:
1. For each item_name, compute avg/min/max chaos_value from item_snapshots where snapshot_at is in the past 24h
2. Insert one row into price_history per item
3. Delete item_snapshots rows older than 30 days

### Modified files
- `app/scheduler.py` — add `compact_price_history()` async function, registered as cron job `0 3 * * *`

## Implementation Order

1. Trade search page (3.1 + 3.2) — most user-facing value
2. Dashboard top movers (3.3 + 3.4) — home page upgrade
3. Purchase tracking (3.5) — simple read-only page
4. Deal detail (3.6) — enriches existing monitor
5. Data compaction (3.7) — background maintenance

Total: 4 new files, 5 modified files, ~500 lines estimated.
