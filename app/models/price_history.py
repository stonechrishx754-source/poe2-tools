"""Compressed time-series price data for fast chart queries."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    data_source: Mapped[str] = mapped_column(String(32), nullable=False)  # poe_ninja / stash / trade
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # currency / unique_item / gem / map
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    variant: Mapped[str] = mapped_column(String(64), default="")
    price_chaos: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_divine: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
