from pydantic import BaseModel


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
