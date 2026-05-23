"""Item & Gem service — save & query price data from poe2scout."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import ItemSnapshot
from app.models.gem import GemSnapshot
from app.models.price_history import PriceHistory

logger = logging.getLogger(__name__)


# ── Save ──

async def save_poe2scout_items(
    db: AsyncSession,
    league_id: int,
    items: list[dict[str, Any]],
    snapshot_at: datetime | None = None,
) -> int:
    """Save items from poe2scout API /Items.

    Each item has: ItemId, CategoryApiId, Text, Name, Type, CurrentPrice, IconUrl.
    Items include uniques, gems, maps, etc. — we map CategoryApiId to item_type.
    """
    if snapshot_at is None:
        snapshot_at = datetime.now(timezone.utc)

    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue

        item_name = item.get("Name") or item.get("name") or item.get("Text", "")
        if not item_name:
            continue

        cat = item.get("CategoryApiId", item.get("category", "unknown"))
        chaos_value = item.get("CurrentPrice") or item.get("currentPrice") or item.get("chaosValue")

        snap = ItemSnapshot(
            league_id=league_id,
            item_name=str(item_name)[:128],
            item_type=str(cat)[:64],
            chaos_value=float(chaos_value) if chaos_value else None,
            low_confidence=False,
            listing_count=item.get("ListingCount", item.get("listingCount")),
            variant=(item.get("Type") or item.get("type") or "")[:64] or None,
            icon_url=item.get("IconUrl", item.get("iconUrl")),
            details_json=json.dumps(item),
            snapshot_at=snapshot_at,
        )
        db.add(snap)
        count += 1

    await db.commit()
    logger.info("Saved %d item snapshots (league_id=%d)", count, league_id)
    return count


async def save_poe2scout_uniques(
    db: AsyncSession,
    league_id: int,
    unique_categories: list[dict[str, Any]],
    snapshot_at: datetime | None = None,
) -> int:
    """Save unique items from poe2scout API /Uniques/ByCategory.

    Response is a list of categories, each containing a list of unique items.
    """
    if snapshot_at is None:
        snapshot_at = datetime.now(timezone.utc)

    count = 0
    for category in unique_categories:
        if not isinstance(category, dict):
            continue

        items = category.get("items", category.get("uniques", []))
        cat_name = category.get("category", category.get("name", "Unknown"))

        for item in items:
            if not isinstance(item, dict):
                continue

            item_name = item.get("Name") or item.get("name", "")
            if not item_name:
                continue

            chaos_value = (
                item.get("CurrentPrice") or
                item.get("currentPrice") or
                item.get("chaosValue")
            )

            snap = ItemSnapshot(
                league_id=league_id,
                item_name=str(item_name)[:128],
                item_type=f"Unique{cat_name}"[:64],
                chaos_value=float(chaos_value) if chaos_value else None,
                low_confidence=False,
                listing_count=item.get("ListingCount"),
                variant=(item.get("Type") or item.get("type") or "")[:64] or None,
                details_json=json.dumps(item),
                snapshot_at=snapshot_at,
            )
            db.add(snap)
            count += 1

    await db.commit()
    logger.info("Saved %d unique item snapshots (league_id=%d)", count, league_id)
    return count


# ── Query ──

async def get_latest_items(
    db: AsyncSession,
    league_id: int,
    item_type: str | None = None,
    sort_by: str = "chaos_value",
    order: str = "desc",
    limit: int = 100,
) -> list[dict]:
    """Get the most recent item snapshot for each item name."""
    conditions = [ItemSnapshot.league_id == league_id]
    if item_type:
        conditions.append(ItemSnapshot.item_type == item_type)

    subq = (
        select(
            ItemSnapshot.item_name,
            func.max(ItemSnapshot.snapshot_at).label("max_at"),
        )
        .where(*conditions)
        .group_by(ItemSnapshot.item_name)
    ).subquery()

    order_col = getattr(ItemSnapshot, sort_by, ItemSnapshot.chaos_value)
    order_expr = order_col.desc() if order == "desc" else order_col.asc()

    query = (
        select(ItemSnapshot)
        .join(
            subq,
            and_(
                ItemSnapshot.item_name == subq.c.item_name,
                ItemSnapshot.snapshot_at == subq.c.max_at,
            ),
        )
        .order_by(order_expr)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.item_name,
            "type": r.item_type,
            "chaos_value": r.chaos_value,
            "divine_value": r.divine_value,
            "listing_count": r.listing_count,
            "variant": r.variant,
            "icon_url": r.icon_url,
            "snapshot_at": r.snapshot_at.isoformat() if r.snapshot_at else None,
        }
        for r in rows
    ]


async def get_latest_gems(
    db: AsyncSession,
    league_id: int,
    gem_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Get the most recent gem snapshot."""
    conditions = [GemSnapshot.league_id == league_id]
    if gem_type:
        conditions.append(GemSnapshot.gem_type == gem_type)

    subq = (
        select(
            GemSnapshot.gem_name,
            GemSnapshot.gem_level,
            func.max(GemSnapshot.snapshot_at).label("max_at"),
        )
        .where(*conditions)
        .group_by(GemSnapshot.gem_name, GemSnapshot.gem_level)
    ).subquery()

    query = (
        select(GemSnapshot)
        .join(
            subq,
            and_(
                GemSnapshot.gem_name == subq.c.gem_name,
                GemSnapshot.gem_level == subq.c.gem_level,
                GemSnapshot.snapshot_at == subq.c.max_at,
            ),
        )
        .order_by(GemSnapshot.chaos_value.desc().nullslast())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.gem_name,
            "type": r.gem_type,
            "level": r.gem_level,
            "quality": r.gem_quality,
            "corruption": r.corruption,
            "chaos_value": r.chaos_value,
            "divine_value": r.divine_value,
            "listing_count": r.listing_count,
            "snapshot_at": r.snapshot_at.isoformat() if r.snapshot_at else None,
        }
        for r in rows
    ]
