"""SSE endpoint + watchlist CRUD + deal list + mark-purchased API."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette import EventSourceResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.deal_alert import DealAlert
from app.models.purchase_log import PurchaseLog
from app.models.watchlist import WatchlistRule


class WatchlistCreate(BaseModel):
    name: str
    item_name: str = ""
    item_type: str | None = None
    max_price: float | None = None
    min_discount: float = 0.15
    is_active: bool = True
    notify_sound: bool = True
    notify_browser: bool = True
    auto_copy_whisper: bool = False
    league_id: int = 1


class WatchlistUpdate(BaseModel):
    name: str | None = None
    item_name: str | None = None
    item_type: str | None = None
    max_price: float | None = None
    min_discount: float | None = None
    is_active: bool | None = None
    notify_sound: bool | None = None
    notify_browser: bool | None = None
    auto_copy_whisper: bool | None = None


router = APIRouter()

# Set by main.py during startup
alert_service = None
monitor_service = None


def _get_svc(request):
    return request.app.state


@router.get("/monitor/stream")
async def deal_stream():
    """SSE endpoint for live deal notifications."""
    if alert_service is None:
        return JSONResponse({"error": "Alert service not initialized"}, 503)
    return EventSourceResponse(alert_service.stream())


@router.get("/watchlist")
async def list_rules(db: AsyncSession = Depends(get_db)):
    """List all watchlist rules."""
    result = await db.execute(
        select(WatchlistRule).order_by(desc(WatchlistRule.created_at))
    )
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "item_name": r.item_name,
            "item_type": r.item_type,
            "max_price": r.max_price,
            "min_discount": r.min_discount,
            "is_active": r.is_active,
            "notify_sound": r.notify_sound,
            "notify_browser": r.notify_browser,
            "auto_copy_whisper": r.auto_copy_whisper,
        }
        for r in rules
    ]


@router.post("/watchlist")
async def create_rule(rule: WatchlistCreate, db: AsyncSession = Depends(get_db)):
    """Create a new watchlist rule."""
    r = WatchlistRule(**rule.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    if r.is_active and monitor_service:
        try:
            await monitor_service.start_rule(r)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to start monitoring for rule %d: %s", r.id, e
            )
    return {"id": r.id, "name": r.name, "is_active": r.is_active}


@router.put("/watchlist/{rule_id}")
async def update_rule(rule_id: int, data: WatchlistUpdate, db: AsyncSession = Depends(get_db)):
    """Update a rule and sync monitoring state."""
    result = await db.execute(
        select(WatchlistRule).where(WatchlistRule.id == rule_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        return JSONResponse({"error": "Not found"}, 404)

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(r, key, val)
    await db.commit()
    await db.refresh(r)

    if monitor_service:
        try:
            was_running = monitor_service.is_running(rule_id)
            if r.is_active and not was_running:
                await monitor_service.start_rule(r)
            elif not r.is_active and was_running:
                await monitor_service.stop_rule(rule_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to sync monitoring for rule %d: %s", rule_id, e
            )

    return {"id": r.id, "name": r.name, "is_active": r.is_active}


@router.delete("/watchlist/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a rule and stop monitoring."""
    result = await db.execute(
        select(WatchlistRule).where(WatchlistRule.id == rule_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        return JSONResponse({"error": "Not found"}, 404)

    if monitor_service:
        await monitor_service.stop_rule(rule_id)
    await db.delete(r)
    await db.commit()
    return {"deleted": True}


@router.get("/deals")
async def list_deals(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent deal alerts."""
    result = await db.execute(
        select(DealAlert).order_by(desc(DealAlert.created_at)).limit(limit)
    )
    deals = result.scalars().all()
    return [
        {
            "id": d.id,
            "item_name": d.item_name,
            "price_amount": d.price_amount,
            "price_currency": d.price_currency,
            "market_avg": d.market_avg,
            "discount_pct": d.discount_pct,
            "seller_account": d.seller_account,
            "whisper_message": d.whisper_message,
            "trade_url": d.trade_url,
            "status": d.status,
        }
        for d in deals
    ]


class MarkPurchased(BaseModel):
    notes: str = ""


@router.put("/deals/{deal_id}/mark-purchased")
async def mark_purchased(
    deal_id: int,
    data: MarkPurchased = MarkPurchased(),
    db: AsyncSession = Depends(get_db),
):
    """Mark a deal as purchased and create PurchaseLog entry."""
    result = await db.execute(
        select(DealAlert).where(DealAlert.id == deal_id)
    )
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
        notes=data.notes,
    )
    db.add(log)
    await db.commit()
    return {"id": deal.id, "status": "purchased"}
