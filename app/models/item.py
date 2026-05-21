"""Item snapshot model — prices from poe.ninja itemoverview."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ItemSnapshot(Base):
    __tablename__ = "item_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)  # UniqueArmour, UniqueWeapon, UniqueJewel, UniqueFlask, Map
    chaos_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    divine_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    exalted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    listing_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)  # corrupted, quality, links
    icon_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
