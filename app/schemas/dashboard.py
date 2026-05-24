from pydantic import BaseModel, Field


class MoverItem(BaseModel):
    item_name: str = ""
    recent_avg: float = 0
    prev_avg: float = 0
    change_pct: float = 0
    icon_url: str | None = None


class CrawlStatusResponse(BaseModel):
    source: str
    status: str
    items_count: int | None = None
    duration_s: float | None = None
    started_at: str | None = None
    error_msg: str | None = None


class DashboardSummary(BaseModel):
    total_currencies: int = 0
    total_items: int = 0
    total_gems: int = 0
    last_crawl: str | None = None
    active_league: str = ""
    top_gainers: list[MoverItem] = Field(default_factory=list)
    top_losers: list[MoverItem] = Field(default_factory=list)
