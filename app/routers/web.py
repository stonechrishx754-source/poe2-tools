"""HTML page routes — Jinja2 + HTMX pages with i18n and item images."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.models.currency import CurrencySnapshot
from app.services.currency_service import (
    get_latest_prices,
    get_or_create_league,
    get_price_history,
    is_currency_excluded,
)
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

    return templates.TemplateResponse(
        request, "index.html",
        _ctx(request, league=league, last_crawl=last_crawl, total_entries=total_entries),
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
