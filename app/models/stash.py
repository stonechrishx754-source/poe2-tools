"""StashTab model — represents a PoE2 stash tab snapshot."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StashTab(Base):
    __tablename__ = "stash_tabs"

    id: Mapped[int] = mapped_column(primary_key=True)
    stash_id: Mapped[str] = mapped_column(String(128), unique=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    account_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stash_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
