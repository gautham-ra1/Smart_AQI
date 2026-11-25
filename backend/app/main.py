"""VayuMesh FastAPI + Socket.io ASGI application entry point."""

from __future__ import annotations

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, advisories, auth, citizens, heatmap, ingestion, sensors
from app.config import get_settings
from app.core.exceptions import register_exception_handlers, success_response
from app.realtime.socket_manager import sio

settings = get_settings()

app = FastAPI(
    title="VayuMesh — Hyperlocal AQI Sensor Fusion API",
    description=(
        "Adaptive Three-Tier Sensor Fusion Engine (Chikkamagaluru pilot) with "
        "Hygrometric Pre-Calibration, Two-Tier EWMA Trust Scoring, "
        "Trust-Weighted IDW & Trust-Aware Ordinary Kriging, and CPCB/MoHFW Health Advisories."
    ),
    version="1.0.0",
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
app.include_router(admin.router)


@app.get("/health", tags=["System"])
async def health():
    return success_response(
        {
            "status": "ok",
            "service": settings.APP_NAME,
            "default_city": settings.DEFAULT_CITY,
        }
    )


# Mount Socket.io ASGI wrapper so uvicorn app.main:socket_app serves both REST + Socket.io
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
