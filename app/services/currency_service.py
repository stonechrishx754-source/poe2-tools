"""Currency & league service — save & query price data from poe2scout."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency import CurrencySnapshot
from app.models.league import League
from app.models.price_history import PriceHistory

logger = logging.getLogger(__name__)

EXCLUDED_CURRENCIES = {
    "chance shard", "transmutation shard", "regal shard",
    "ancient shard", "mirror shard", "artificer's shard",
}


def is_currency_excluded(name: str) -> bool:
    """Return True if a currency should be excluded from the main listing."""
    name_lower = name.lower()
    if name_lower in EXCLUDED_CURRENCIES:
        return True
    if "greater" in name_lower or "perfect" in name_lower:
        return True
    return False


# ── League ──

async def get_or_create_league(db: AsyncSession, name: str) -> League:
    """Find or create a league row."""
    query = select(League).where(League.name == name)
    result = await db.execute(query)
    league = result.scalar_one_or_none()
    if league is None:
        league = League(name=name, is_active=True)
        db.add(league)
        await db.commit()
        await db.refresh(league)
    return league


async def update_league_prices(
    db: AsyncSession, league_name: str, divine_price: float | None,
    chaos_divine_price: float | None,
):
    """Update league with current divine/chaos exchange rates."""
    league = await get_or_create_league(db, league_name)
    # We can store these in a settings-style table or just log them
    logger.debug("League %s: divine=%s, chaos_divine=%s", league_name, divine_price, chaos_divine_price)


# ── Save currency data from poe2scout ──

async def save_poe2scout_currencies(
    db: AsyncSession,
    league_id: int,
    currency_categories: list[dict[str, Any]],
    snapshot_at: datetime | None = None,
) -> int:
    """Save currency data from poe2scout API /Currencies/ByCategory.

    The API returns categories, each containing a list of currencies.
    Stores each currency as a CurrencySnapshot.
    """
    if snapshot_at is None:
        snapshot_at = datetime.now(timezone.utc)

    count = 0
    for category in currency_categories:
        # category might be a list of currencies or a dict with items
        if isinstance(category, dict):
            currencies = category.get("items", category.get("currencies", []))
            cat_name = category.get("category", category.get("name", "Unknown"))
        elif isinstance(category, list):
            currencies = category
            cat_name = "Unknown"
        else:
            continue

        for curr in currencies:
            if isinstance(curr, dict):
                curr_name = (
                    curr.get("currencyTypeName") or
                    curr.get("name") or
                    curr.get("text", "")
                )
                if not curr_name:
                    continue

                chaos_val = (
                    curr.get("chaosEquivalent") or
                    curr.get("price") or
                    curr.get("currentPrice") or
                    curr.get("chaosValue", 0)
                )

                snap = CurrencySnapshot(
                    league_id=league_id,
                    currency_name=str(curr_name)[:64],
                    currency_type=str(cat_name)[:32],
                    chaos_equivalent=float(chaos_val) if chaos_val else 0,
                    low_confidence=curr.get("lowConfidence", False),
                    snapshot_at=snapshot_at,
                    details_json=json.dumps(curr),
                )
                db.add(snap)
                count += 1

    await db.commit()
    logger.info("Saved %d currency snapshots (league_id=%d)", count, league_id)
    return count


# ── Query ──

async def get_latest_prices(db: AsyncSession, league_id: int) -> list[dict]:
    """Get the most recent currency snapshot for each currency name."""
    subq = (
        select(
            CurrencySnapshot.currency_name,
            func.max(CurrencySnapshot.snapshot_at).label("max_at"),
        )
        .where(CurrencySnapshot.league_id == league_id)
        .group_by(CurrencySnapshot.currency_name)
    ).subquery()

    query = (
        select(CurrencySnapshot)
        .join(
            subq,
            and_(
                CurrencySnapshot.currency_name == subq.c.currency_name,
                CurrencySnapshot.snapshot_at == subq.c.max_at,
            ),
        )
        .order_by(CurrencySnapshot.currency_type, CurrencySnapshot.chaos_equivalent.desc())
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.currency_name,
            "type": r.currency_type,
            "chaos_value": r.chaos_equivalent,
            "low_confidence": r.low_confidence,
            "snapshot_at": r.snapshot_at.isoformat() if r.snapshot_at else None,
        }
        for r in rows
    ]


async def get_price_history(
    db: AsyncSession,
    league_id: int,
    entity_name: str,
    days: int = 7,
) -> list[dict]:
    """Get price history for chart rendering."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(PriceHistory)
        .where(
            PriceHistory.league_id == league_id,
            PriceHistory.entity_name == entity_name,
            PriceHistory.recorded_at >= cutoff,
        )
        .order_by(PriceHistory.recorded_at)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "price_chaos": r.price_chaos,
            "price_divine": r.price_divine,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]
