import hashlib
import logging
from typing import Any

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.deal_alert import DealAlert
from app.models.item import ItemSnapshot

logger = logging.getLogger(__name__)


class DealService:
    """Evaluates incoming Trade2 items -- computes discount, creates alerts."""

    def __init__(self, league_id: int, alert_queue):
        self._league_id = league_id
        self._alert_queue = alert_queue

    async def evaluate(self, rule_id: int, rule_max_price: float | None,
                       rule_min_discount: float, item: dict[str, Any]):
        listing = item.get("listing", {})
        price_data = listing.get("price", {})
        item_data = item.get("item", {})

        price_amount = price_data.get("amount")
        price_currency = price_data.get("currency", "chaos")
        item_name = (item_data.get("name") or item_data.get("typeLine", ""))
        item_type = item_data.get("typeLine", "")

        if not price_amount or not item_name:
            return
        price_amount = float(price_amount)

        if rule_max_price and price_amount > rule_max_price:
            return

        market_avg = await self._get_market_avg(item_name)
        if market_avg is None or market_avg <= 0:
            logger.debug("DealService: no market data for %s, skipping", item_name)
            return

        discount_pct = (market_avg - price_amount) / market_avg
        if discount_pct < rule_min_discount:
            return

        trade2_id = hashlib.md5(item_name.encode()).hexdigest()[:12]
        whisper = listing.get("whisper", "")
        trade_url = (
            f"https://www.pathofexile.com/trade2/search/poe2/"
            f"Fate%20of%20the%20Vaal/{trade2_id}"
        )

        async with AsyncSessionLocal() as db:
            alert = DealAlert(
                rule_id=rule_id,
                trade2_id=str(item.get("id", "")),
                item_name=item_name,
                item_type=item_type,
                item_json=str(item),
                seller_account=listing.get("account", {}).get("name", ""),
                seller_character=listing.get("account", {}).get("lastCharacterName", ""),
                price_amount=price_amount,
                price_currency=price_currency,
                market_avg=round(market_avg, 2),
                discount_pct=round(discount_pct * 100, 1),
                whisper_message=whisper,
                trade_url=trade_url,
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)

            msg = {
                "id": alert.id,
                "item_name": item_name,
                "price_amount": price_amount,
                "price_currency": price_currency,
                "market_avg": round(market_avg, 2),
                "discount_pct": round(discount_pct * 100, 1),
                "seller": listing.get("account", {}).get("name", ""),
                "whisper_message": whisper,
                "trade_url": trade_url,
            }
            await self._alert_queue.put(msg)
            logger.info("DealService: ALERT %s %.1f%% OFF", item_name, discount_pct * 100)

    async def _get_market_avg(self, item_name: str) -> float | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.avg(ItemSnapshot.chaos_value))
                .where(ItemSnapshot.item_name == item_name)
            )
            avg = result.scalar()
            return float(avg) if avg else None
