"""REST API endpoints for item and gem data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.item import ItemResponse, GemResponse
from app.services.currency_service import get_or_create_league
from app.services.item_service import get_latest_items, get_latest_gems

router = APIRouter()


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    league: str = Query("Fate of the Vaal"),
    item_type: str = Query(None),
    sort: str = Query("chaos_value"),
    order: str = Query("desc"),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get latest item prices."""
    league_obj = await get_or_create_league(db, league)
    return await get_latest_items(
        db, league_obj.id,
        item_type=item_type,
        sort_by=sort,
        order=order,
        limit=limit,
    )


@router.get("/gems", response_model=list[GemResponse])
async def list_gems(
    league: str = Query("Fate of the Vaal"),
    gem_type: str = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get latest gem prices."""
    league_obj = await get_or_create_league(db, league)
    return await get_latest_gems(db, league_obj.id, gem_type=gem_type, limit=limit)
