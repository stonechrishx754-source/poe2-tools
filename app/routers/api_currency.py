"""REST API endpoints for currency data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.currency import CurrencyResponse, PriceHistoryPoint
from app.services.currency_service import (
    get_latest_prices,
    get_or_create_league,
    get_price_history,
)

router = APIRouter()


@router.get("/currency", response_model=list[CurrencyResponse])
async def list_currencies(
    league: str = Query("Fate of the Vaal"),
    db: AsyncSession = Depends(get_db),
):
    """Get latest currency prices for a league."""
    league_obj = await get_or_create_league(db, league)
    return await get_latest_prices(db, league_obj.id)


@router.get("/currency/{name}/history", response_model=list[PriceHistoryPoint])
async def currency_history(
    name: str,
    league: str = Query("Fate of the Vaal"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get price history for a specific currency."""
    league_obj = await get_or_create_league(db, league)
    return await get_price_history(db, league_obj.id, name, days=days)
