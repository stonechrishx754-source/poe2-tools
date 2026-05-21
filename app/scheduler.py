"""APScheduler setup — cron/interval jobs for data collection."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.crawl_log import CrawlLog
from app.services.currency_service import (
    get_or_create_league,
    save_poe2scout_currencies,
)
from app.services.item_service import save_poe2scout_items, save_poe2scout_uniques

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

    scheduler.start()
    logger.info("Scheduler started: every %d minutes", settings.CRAWL_INTERVAL_MINUTES)
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler):
    """Gracefully stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
