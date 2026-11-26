"""VayuMesh FastAPI + Socket.io ASGI entry point with background live official station sync."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, advisories, analytics, auth, citizens, heatmap, ingestion, sensors
from app.config import get_settings
from app.core.exceptions import register_exception_handlers, success_response
from app.database import AsyncSessionLocal
from app.integrations.official_sync import sync_official_stations_live
from app.realtime.socket_manager import sio
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("vayumesh.main")


async def _official_poller_loop() -> None:
    """Periodically sync official Kalyana Nagara KSPCB station from live CPCB/OpenAQ/Open-Meteo."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                synced = await sync_official_stations_live(db=db, city=settings.DEFAULT_CITY)
                if synced:
                    logger.info(
                        "Synced %d official station(s) via %s",
                        len(synced),
                        synced[0].get("live_source"),
                    )
        except Exception as exc:
            logger.warning("Background official sync skipped: %s", exc)
        await asyncio.sleep(600)  # Every 10 minutes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_official_poller_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="VayuMesh — Hyperlocal AQI Sensor Fusion API",
    description=(
        "Adaptive Three-Tier Sensor Fusion Engine (Chikkamagaluru – Sringeri Corridor) with "
        "Satellite+Ground Fusion, Hygrometric Pre-Calibration, Two-Tier EWMA Trust Scoring, "
        "High-Res Trust-Weighted IDW & Trust-Aware Ordinary Kriging, and CPCB/MoHFW Advisories."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(citizens.router)
app.include_router(sensors.router)
app.include_router(ingestion.router)
app.include_router(heatmap.router)
app.include_router(advisories.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.get("/health", tags=["System"])
async def health():
    return success_response(
        {
            "status": "ok",
            "service": settings.APP_NAME,
            "default_city": settings.DEFAULT_CITY,
            "version": "2.0.0",
        }
    )


socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
