"""REST API endpoints for dashboard data (crawl status, summary)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.models.currency import CurrencySnapshot
from app.models.gem import GemSnapshot
from app.models.item import ItemSnapshot
from app.schemas.dashboard import CrawlStatusResponse, DashboardSummary
from app.services.analysis_service import get_top_movers
from app.services.currency_service import get_or_create_league

router = APIRouter()

# Cached league list — refreshed on startup and periodically
_cached_leagues: list[dict] = []
_last_league_refresh = 0.0


@router.get("/leagues")
async def list_leagues():
    """Get available POE2 leagues from poe2scout."""
    import time
    from app.crawlers.poe2scout import Poe2ScoutCrawler
    global _cached_leagues, _last_league_refresh

    if not _cached_leagues or time.time() - _last_league_refresh > 3600:
        crawler = Poe2ScoutCrawler()
        try:
            raw = await crawler.fetch_leagues()
            _cached_leagues = [
                {"name": r["Value"], "short": r["ShortName"], "current": r["IsCurrent"]}
                for r in raw if isinstance(r, dict)
            ]
            _last_league_refresh = time.time()
        except Exception:
            pass
        finally:
            await crawler.close()

    return _cached_leagues


@router.get("/dashboard/crawl-status", response_model=list[CrawlStatusResponse])
async def crawl_status(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get recent crawl logs."""
    query = (
        select(CrawlLog)
        .order_by(desc(CrawlLog.started_at))
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        CrawlStatusResponse(
            source=log.source,
            status=log.status,
            items_count=log.items_count,
            duration_s=log.duration_s,
            started_at=log.started_at.isoformat() if log.started_at else None,
            error_msg=log.error_msg,
        )
        for log in logs
    ]


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    league: str = Query("Fate of the Vaal"),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate dashboard summary."""
    league_obj = await get_or_create_league(db, league)

    currency_count = await db.scalar(
        select(func.count(CurrencySnapshot.id))
        .where(CurrencySnapshot.league_id == league_obj.id)
    )
    item_count = await db.scalar(
        select(func.count(ItemSnapshot.id))
        .where(ItemSnapshot.league_id == league_obj.id)
    )
    gem_count = await db.scalar(
        select(func.count(GemSnapshot.id))
        .where(GemSnapshot.league_id == league_obj.id)
    )

    last_crawl_result = await db.execute(
        select(CrawlLog)
        .where(CrawlLog.source == "poe2scout", CrawlLog.status == "success")
        .order_by(desc(CrawlLog.started_at))
        .limit(1)
    )
    last_crawl = last_crawl_result.scalar_one_or_none()

    gainers = await get_top_movers(db, league_obj.id, "gainers", 5)
    losers = await get_top_movers(db, league_obj.id, "losers", 5)

    return DashboardSummary(
        total_currencies=currency_count or 0,
        total_items=item_count or 0,
        total_gems=gem_count or 0,
        last_crawl=last_crawl.started_at.isoformat() if last_crawl else None,
        active_league=league,
        top_gainers=gainers,
        top_losers=losers,
    )
