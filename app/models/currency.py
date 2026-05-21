"""Currency snapshot model — prices from poe.ninja currencyoverview."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CurrencySnapshot(Base):
    __tablename__ = "currency_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    currency_name: Mapped[str] = mapped_column(String(64), nullable=False)
    currency_type: Mapped[str] = mapped_column(String(32), default="Currency")  # Currency / Fragment
    chaos_equivalent: Mapped[float] = mapped_column(Float, nullable=False)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
