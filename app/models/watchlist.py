"""WatchlistRule model — defines a user's watchlist rule for deal detection."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WatchlistRule(Base):
    __tablename__ = "watchlist_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    item_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_discount: Mapped[float] = mapped_column(Float, default=0.15)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_sound: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_browser: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_copy_whisper: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
