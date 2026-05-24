"""DealAlert model — records a detected deal from watchlist monitoring."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DealAlert(Base):
    __tablename__ = "deal_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    trade2_id: Mapped[str] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(128))
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seller_character: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_amount: Mapped[float] = mapped_column(Float, nullable=False)
    price_currency: Mapped[str] = mapped_column(String(32), default="chaos")
    market_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    whisper_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
