"""APScheduler setup — cron/interval jobs for data collection."""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, func, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.crawl_log import CrawlLog
from app.models.item import ItemSnapshot
from app.services.currency_service import (
    get_or_create_league,
    save_poe2scout_currencies,
)
from app.services.item_service import save_poe2scout_items, save_poe2scout_uniques
from app.crawlers.ggg_stash import GggStashCrawler

logger = logging.getLogger(__name__)


async def crawl_data():
    """Scheduled job: fetch all POE2 data from poe2scout for all configured leagues."""
    from app.crawlers.poe2scout import Poe2ScoutCrawler

    crawler = Poe2ScoutCrawler()
    snapshot_at = datetime.now(timezone.utc)

    for league_name in settings.league_list:
        start = datetime.now(timezone.utc)
        status = "success"
        total_items = 0
        error_msg = None

        try:
            async with AsyncSessionLocal() as db:
                league = await get_or_create_league(db, league_name)

                # Currencies by category
                currency_categories = await crawler.fetch_currencies_by_category(league_name)
                total_items += await save_poe2scout_currencies(
                    db, league.id, currency_categories, snapshot_at
                )

                # Unique items by category
                unique_categories = await crawler.fetch_uniques_by_category(league_name)
                total_items += await save_poe2scout_uniques(
                    db, league.id, unique_categories, snapshot_at
                )

                # All items
                items = await crawler.fetch_items(league_name)
                total_items += await save_poe2scout_items(
                    db, league.id, items, snapshot_at
                )

            logger.info(
                "Crawl for '%s': %d items saved", league_name, total_items,
            )

        except Exception as e:
            status = "failed"
            error_msg = str(e)
            logger.error("Crawl failed for '%s': %s", league_name, e)

        finally:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            async with AsyncSessionLocal() as db:
                log = CrawlLog(
                    source="poe2scout",
                    status=status,
                    items_count=total_items,
                    error_msg=error_msg,
                    duration_s=duration,
                    started_at=start,
                )
                db.add(log)
                await db.commit()

    await crawler.close()


async def crawl_stash():
    """Scheduled: poll GGG Public Stash API."""
    crawler = GggStashCrawler()
    await crawler.load_cursor()
    start = datetime.now(timezone.utc)
    error_msg = None
    try:
        items, new_cursor = await crawler.poll()
        if new_cursor:
            crawler.next_change_id = new_cursor
            crawler.save_cursor()
        logger.info("ggg_stash: polled %d priced items", len(items))
        async with AsyncSessionLocal() as db:
            log = CrawlLog(source="ggg_stash", status="success",
                           items_count=len(items), duration_s=(datetime.now(timezone.utc) - start).total_seconds(), started_at=start)
            db.add(log)
            await db.commit()
    except Exception as e:
        error_msg = str(e)
        logger.error("ggg_stash poll failed: %s", e)
    finally:
        await crawler.close()


async def compact_price_history():
    """Daily: aggregate item_snapshots into price_history, prune old data."""
    from app.models.price_history import PriceHistory

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    threshold = datetime.now(timezone.utc) - timedelta(days=30)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                ItemSnapshot.item_name,
                ItemSnapshot.league_id,
                func.avg(ItemSnapshot.chaos_value).label("avg_val"),
                func.min(ItemSnapshot.chaos_value).label("min_val"),
                func.max(ItemSnapshot.chaos_value).label("max_val"),
                func.count(ItemSnapshot.id).label("sample_size"),
            )
            .where(
                ItemSnapshot.snapshot_at >= yesterday,
                ItemSnapshot.snapshot_at < today,
                ItemSnapshot.chaos_value.isnot(None),
            )
            .group_by(ItemSnapshot.item_name, ItemSnapshot.league_id)
        )
        rows = result.all()

        compacted = 0
        for r in rows:
            ph = PriceHistory(
                league_id=r.league_id,
                data_source="poe_ninja",
                entity_type="item",
                entity_name=r.item_name,
                price_chaos=round(r.avg_val, 2),
                sample_size=r.sample_size,
                recorded_at=today,
            )
            db.add(ph)
            compacted += 1

        del_result = await db.execute(
            delete(ItemSnapshot).where(ItemSnapshot.snapshot_at < threshold)
        )
        deleted = del_result.rowcount

        await db.commit()
        logger.info("Compaction: %d price_history rows, %d old snapshots deleted", compacted, deleted)


def start_scheduler() -> AsyncIOScheduler:
    """Create, configure, and start the APScheduler instance."""
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(
        crawl_data,
        "interval",
        minutes=settings.CRAWL_INTERVAL_MINUTES,
        id="data_sync",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        crawl_stash,
        "interval",
        minutes=settings.STASH_INTERVAL_MINUTES,
        id="stash_poll",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        compact_price_history,
        "cron", hour=3, minute=0,
        id="price_compaction",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started: every %d minutes", settings.CRAWL_INTERVAL_MINUTES)
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler):
    """Gracefully stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
