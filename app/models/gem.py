"""Gem snapshot model — prices from poe.ninja gemoverview."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GemSnapshot(Base):
    __tablename__ = "gem_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    gem_name: Mapped[str] = mapped_column(String(128), nullable=False)
    gem_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SkillGem / SupportGem
    gem_level: Mapped[int] = mapped_column(Integer, default=1)
    gem_quality: Mapped[int] = mapped_column(Integer, default=0)
    corruption: Mapped[str | None] = mapped_column(String(16), nullable=True)  # NULL / corrupted / vaal
    chaos_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    divine_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    listing_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
