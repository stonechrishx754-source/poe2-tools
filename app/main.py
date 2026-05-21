"""FastAPI application entry point.

Wires together: database, scheduler, routers, templates, static files.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db
from app.models.base import Base
from app.routers import web, api_currency, api_items, api_dashboard
from app.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")


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

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down POE2 Analytics...")
    stop_scheduler(scheduler)
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
