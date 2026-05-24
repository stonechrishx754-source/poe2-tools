"""HTML page routes — Jinja2 + HTMX pages with i18n and item images."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.models.currency import CurrencySnapshot
from app.services.currency_service import (
    get_latest_prices,
    get_or_create_league,
    get_price_history,
    is_currency_excluded,
)
from app.services.analysis_service import get_top_movers
from app.services.item_service import get_latest_items, get_latest_gems
from app.template_setup import create_templates

router = APIRouter()
templates = create_templates()


def _active_league(request: Request) -> str:
    return request.query_params.get("league", "Fate of the Vaal")


def _locale(request: Request) -> str:
    """Extract locale from query param (lang=zh|en), default zh."""
    lang = request.query_params.get("lang", "zh")
    return "en" if lang == "en" else "zh"


def _ctx(request: Request, **extra) -> dict:
    """Build template context with common variables."""
    ctx = {
        "request": request,
        "league": _active_league(request),
        "locale": _locale(request),
    }
    ctx.update(extra)
    return ctx


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)

    log_query = (
        select(CrawlLog)
        .where(CrawlLog.source == "poe2scout")
        .order_by(desc(CrawlLog.started_at))
        .limit(1)
    )
    log_result = await db.execute(log_query)
    last_crawl = log_result.scalar_one_or_none()

    count_currency = await db.execute(
        select(func.count(CurrencySnapshot.id))
        .where(CurrencySnapshot.league_id == league_obj.id)
    )
    total_entries = count_currency.scalar() or 0

    gainers = await get_top_movers(db, league_obj.id, "gainers", 5)
    losers = await get_top_movers(db, league_obj.id, "losers", 5)

    return templates.TemplateResponse(
        request, "index.html",
        _ctx(request, league=league, last_crawl=last_crawl, total_entries=total_entries,
             top_gainers=gainers, top_losers=losers),
    )


@router.get("/currency", response_class=HTMLResponse)
async def currency_page(
    request: Request,
    sort: str = Query("chaos_value"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)

    # Fetch currency items from item_snapshots (category = "currency")
    raw_items = await get_latest_items(
        db, league_obj.id, item_type="currency",
        sort_by="chaos_value", order="desc", limit=100,
    )

    # Normalize currency prices against Chaos Orb as the base value.
    # The API's CurrentPrice is an abstract index; dividing each by the Chaos Orb's
    # index gives the real chaos-equivalent value. Divine Orb ratio is verified
    # against the League API's ChaosDivinePrice field.
    chaos_ref = next((i for i in raw_items if i["name"].lower() == "chaos orb"), None)
    divine_ref = next((i for i in raw_items if i["name"].lower() == "divine orb"), None)

    index_base = chaos_ref.get("chaos_value") if chaos_ref else None
    if index_base:
        for item in raw_items:
            cp = item.get("chaos_value")
            item["chaos_value_real"] = round(cp / index_base, 4) if cp else None

    divine_chaos = None
    if divine_ref and index_base:
        dc_val = divine_ref.get("chaos_value")
        divine_chaos = round(dc_val / index_base, 2) if dc_val else None

    # Filter out shards and essence tiers (logic moved from template)
    raw_items = [i for i in raw_items if not is_currency_excluded(i.get("name", ""))]

    return templates.TemplateResponse(
        request, "currency.html",
        _ctx(request, league=league, items=raw_items,
             divine_chaos=divine_chaos),
    )


@router.get("/currency/{name}", response_class=HTMLResponse)
async def currency_detail(
    request: Request, name: str, db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)
    prices = await get_latest_prices(db, league_obj.id)
    currency_data = next((p for p in prices if p["name"] == name), None)

    if not currency_data:
        loc = _locale(request)
        err = f"Currency '{name}' " + ("not found" if loc == "en" else "未找到")
        return templates.TemplateResponse(
            request, "currency_detail.html",
            _ctx(request, league=league, currency=None, error=err),
        )

    history = await get_price_history(db, league_obj.id, name, days=14)

    return templates.TemplateResponse(
        request, "currency_detail.html",
        _ctx(request, league=league, currency=currency_data, history=history),
    )


@router.get("/items", response_class=HTMLResponse)
async def items_page(
    request: Request,
    item_type: str = Query(None),
    sort: str = Query("chaos_value"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)
    items = await get_latest_items(
        db, league_obj.id, item_type=item_type,
        sort_by=sort, order=order, limit=200,
    )

    return templates.TemplateResponse(
        request, "items.html",
        _ctx(request, league=league, items=items, current_type=item_type or "all"),
    )


@router.get("/items/{name}", response_class=HTMLResponse)
async def item_detail(
    request: Request, name: str, db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)
    items = await get_latest_items(db, league_obj.id, limit=500)
    item_data = next((i for i in items if i["name"] == name), None)

    loc = _locale(request)
    err = (f"Item '{name}' " + ("not found" if loc == "en" else "未找到")) if not item_data else None

    return templates.TemplateResponse(
        request, "item_detail.html",
        _ctx(request, league=league, item=item_data, error=err),
    )


@router.get("/gems", response_class=HTMLResponse)
async def gems_page(
    request: Request,
    gem_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)
    gems = await get_latest_gems(db, league_obj.id, gem_type=gem_type, limit=200)

    return templates.TemplateResponse(
        request, "gems.html",
        _ctx(request, league=league, gems=gems, current_type=gem_type or "all"),
    )


@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    return templates.TemplateResponse(request, "monitor.html", _ctx(request))


@router.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    return templates.TemplateResponse(request, "trades.html", _ctx(request))


@router.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request, db: AsyncSession = Depends(get_db)):
    from app.models.purchase_log import PurchaseLog

    result = await db.execute(
        select(PurchaseLog).order_by(desc(PurchaseLog.purchased_at))
    )
    purchases = result.scalars().all()

    total_spent = sum(p.price_amount for p in purchases)
    total_saved = sum((p.market_avg or p.price_amount) - p.price_amount for p in purchases)
    roi = (total_saved / total_spent * 100) if total_spent > 0 else 0

    return templates.TemplateResponse(
        request, "purchases.html",
        _ctx(request, purchases=purchases, total_spent=round(total_spent, 0),
             total_saved=round(total_saved, 0), roi=round(roi, 1),
             count=len(purchases)),
    )


# ── HTMX Fragments ──

@router.get("/fragments/price-table", response_class=HTMLResponse)
async def price_table_fragment(
    request: Request,
    type: str = Query("currency"),
    sort: str = Query("chaos_value"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)

    if type == "currency" or type == "fragment":
        prices = await get_latest_prices(db, league_obj.id)
        items = [p for p in prices if p["type"] == ("Fragment" if type == "fragment" else "Currency")]
        reverse = order == "desc"
        items.sort(key=lambda x: x.get(sort, 0) or 0, reverse=reverse)
        return templates.TemplateResponse(
            request, "fragments/price_table.html",
            _ctx(request, items=items, columns=["name", "chaos_value"]),
        )
    elif type == "items":
        item_type_filter = request.query_params.get("item_type")
        items = await get_latest_items(
            db, league_obj.id, item_type=item_type_filter,
            sort_by=sort, order=order, limit=200,
        )
        return templates.TemplateResponse(
            request, "fragments/price_table.html",
            _ctx(request, items=items, columns=["name", "chaos_value", "divine_value", "listing_count"]),
        )

    return HTMLResponse("<tr><td colspan='4'>" + ("No data" if _locale(request) == "en" else "暂无数据") + "</td></tr>")


@router.get("/fragments/price-chart", response_class=HTMLResponse)
async def price_chart_fragment(
    request: Request,
    entity: str = Query(...),
    days: int = Query(7),
    db: AsyncSession = Depends(get_db),
):
    league = _active_league(request)
    league_obj = await get_or_create_league(db, league)
    history = await get_price_history(db, league_obj.id, entity, days=days)

    return templates.TemplateResponse(
        request, "fragments/price_chart.html",
        _ctx(request, entity=entity, history=history, days=days),
    )


@router.get("/api/v1/trade/search", response_class=HTMLResponse)
async def trade_search_fragment(
    request: Request,
    name: str = Query(""),
    item_type: str = Query(""),
    max_price: float | None = Query(None),
):
    from app.crawlers.ggg_trade2 import GggTrade2Crawler

    league = _active_league(request)
    crawler = GggTrade2Crawler()
    result = await crawler.search(league, name=name, item_type=item_type, max_price=max_price)
    await crawler.close()

    if "error" in result:
        return HTMLResponse(
            '<div class="text-center text-muted py-4">' + str(result["error"]) + '</div>'
        )

    items = result.get("result", [])
    if not items:
        return HTMLResponse(
            '<div class="text-center text-muted py-4">No items found</div>'
        )

    query_id = result.get("id", "")
    ids = ",".join(items[:10])
    import httpx
    async with httpx.AsyncClient() as c:
        r = await c.get(
            "https://www.pathofexile.com/api/trade2/fetch/" + ids + "?query=" + query_id,
            cookies={"POESESSID": settings.GGG_POESESSID},
        )
        details = r.json().get("result", [])

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

        rows_html += '<tr>'
        if icon:
            rows_html += '<td style="width:40px"><img src="' + icon + '" style="width:32px;height:32px"></td>'
        else:
            rows_html += '<td></td>'
        rows_html += '<td>' + i_name + '</td>'
        rows_html += '<td><span class="badge bg-secondary" style="font-size:.65rem;">' + i_type + '</span></td>'
        rows_html += '<td class="text-end">' + str(p_amount) + ' ' + p_currency + '</td>'
        rows_html += '<td class="text-end">' + seller + '</td>'
        rows_html += '<td><button class="btn btn-sm btn-outline-info" style="font-size:.65rem;" onclick="trackItem(\'' + i_name.replace("'", "\\'") + '\', \'' + i_type.replace("'", "\\'") + '\', ' + str(p_amount) + ')">Track</button></td>'
        rows_html += '</tr>'

    return HTMLResponse(
        '<div class="text-muted small mb-2">Found ' + str(result.get("total", 0)) + ' items</div>'
        '<table class="table table-dark table-sm">'
        '<thead><tr><th></th><th>Name</th><th>Type</th><th class="text-end">Price</th><th class="text-end">Seller</th><th></th></tr></thead>'
        '<tbody>' + rows_html + '</tbody></table>'
    )
