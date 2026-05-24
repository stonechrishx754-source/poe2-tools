"""PurchaseLog model — logs completed purchases from deal alerts."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PurchaseLog(Base):
    __tablename__ = "purchase_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_alert_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_name: Mapped[str] = mapped_column(String(128))
    price_amount: Mapped[float] = mapped_column(Float)
    price_currency: Mapped[str] = mapped_column(String(32), default="chaos")
    market_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    seller_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
