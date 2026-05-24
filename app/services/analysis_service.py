"""Market analysis: top movers, trends from item_snapshots."""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
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
