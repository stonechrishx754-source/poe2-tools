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

    # Compute real chaos-equivalent values using known exchange rates
    # The Items API CurrentPrice is an abstract index.
    # We normalize using the divine:chaos ratio from league data.
    # 1 Divine ≈ ChaosDivinePrice Chaos (tracked via scheduler from poe2scout leagues API)

    # Find the reference items
    chaos_ref = next((i for i in raw_items if i["name"].lower() == "chaos orb"), None)
    divine_ref = next((i for i in raw_items if i["name"].lower() == "divine orb"), None)
    exalted_ref = next((i for i in raw_items if i["name"].lower() == "exalted orb"), None)

    # Get ChaosDivinePrice from crawl_log stored values, or compute from items
    if chaos_ref and divine_ref and divine_ref.get("chaos_value") and chaos_ref.get("chaos_value"):
        # The stored 'chaos_value' is actually the API's CurrentPrice (abstract index)
        # Real chaos = item_cp / chaos_cp ... NO, we need inverted: chaos_cp / item_cp for some items
        # For divine: chaos_cp / divine_cp = a small fraction, but we know 1 divine ≈ 40 chaos
        # Actually: divine_cp / chaos_cp = the chaos:divine ratio (from the API data analysis)
        index_base = chaos_ref["chaos_value"]  # Chaos Orb's CurrentPrice
        if index_base and index_base > 0:
            for item in raw_items:
                cp = item.get("chaos_value")  # This is actually CurrentPrice from API
                if cp and index_base:
                    # Real chaos value: (CurrentPrice_item / CurrentPrice_chaos) is the ratio
                    # For divine: divine_cp / chaos_cp = chaos_divine_ratio
                    # So real chaos value = chaos_cp / item_cp (inverted)
                    # BUT we want item_cp / chaos_cp for display
                    item["chaos_value_real"] = round(cp / index_base, 4)
                else:
                    item["chaos_value_real"] = None
        else:
            for item in raw_items:
                item["chaos_value_real"] = item.get("chaos_value")

    # Divine price (in chaos) for reference
    divine_chaos = None
    if divine_ref and chaos_ref:
        dc_val = divine_ref.get("chaos_value")
        cc_val = chaos_ref.get("chaos_value")
        if dc_val and cc_val:
            divine_chaos = round(dc_val / cc_val, 2)

    # Exalted price (in chaos)
    exalted_chaos = None
    if exalted_ref and chaos_ref:
        ec_val = exalted_ref.get("chaos_value")
        cc_val = chaos_ref.get("chaos_value")
        if ec_val and cc_val:
            exalted_chaos = round(ec_val / cc_val, 2)

    return templates.TemplateResponse(
        request, "currency.html",
        _ctx(request, league=league, items=raw_items,
             divine_chaos=divine_chaos, exalted_chaos=exalted_chaos),
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

    from app.services.currency_service import get_price_history
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
    from app.services.currency_service import get_price_history
    history = await get_price_history(db, league_obj.id, entity, days=days)

    return templates.TemplateResponse(
        request, "fragments/price_chart.html",
        _ctx(request, entity=entity, history=history, days=days),
    )
