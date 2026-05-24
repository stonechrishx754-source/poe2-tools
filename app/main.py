"""FastAPI application entry point.

Wires together: database, scheduler, routers, templates, static files.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine
from app.models.base import Base
from app.routers import web, api_currency, api_items, api_dashboard, api_monitor
from app.scheduler import start_scheduler, stop_scheduler
from app.services.alert_service import AlertService
from app.services.monitor_service import MonitorService
from app.services.deal_service import DealService
from app.config import settings
from app.template_setup import create_templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

templates = create_templates()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: DB init on start, cleanup on shutdown."""
    logger.info("Starting POE2 Analytics application...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")

    # Start background scheduler
    scheduler = start_scheduler()

    # Initialize real-time monitoring services (Phase 2)
    active_league = settings.league_list[0] if settings.league_list else "Fate of the Vaal"
    alert_svc = AlertService()
    deal_svc = DealService(league_name=active_league, alert_queue=alert_svc.queue)
    monitor_svc = MonitorService(
        poesessid=settings.GGG_POESESSID or "",
        league=active_league,
        on_item=lambda item: deal_svc.evaluate(
            rule_id=0, rule_max_price=None, rule_min_discount=0.1, item=item
        ),
    )
    api_monitor.alert_service = alert_svc
    api_monitor.monitor_service = monitor_svc
    app.state.alert_svc = alert_svc
    app.state.monitor_svc = monitor_svc

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down POE2 Analytics...")
    stop_scheduler(scheduler)
    await monitor_svc.close_all()
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="POE2 Analytics",
    description="Path of Exile 2 Data Crawling, Analysis & Trading Monitor",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register routers
app.include_router(web.router)
app.include_router(api_currency.router, prefix="/api/v1")
app.include_router(api_items.router, prefix="/api/v1")
app.include_router(api_dashboard.router, prefix="/api/v1")
app.include_router(api_monitor.router, prefix="/api/v1")


# Error handlers
@app.exception_handler(404)
async def not_found(request: Request, exc):
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            "base.html",
            {"request": request},
            status_code=404,
        )
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": "Not found"}, status_code=404)
