"""Socket.io ASGI manager for real-time heatmap and sensor trust broadcasts."""

from __future__ import annotations

import socketio

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("vayumesh.socket")

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)


@sio.event
async def connect(sid, environ):
    logger.info("Socket client connected: %s", sid)
    await sio.enter_room(sid, "chikkamagaluru")


@sio.event
async def disconnect(sid):
    logger.info("Socket client disconnected: %s", sid)


@sio.event
async def join_city(sid, data):
    city = (data or {}).get("city", "chikkamagaluru").lower()
    await sio.enter_room(sid, city)
    await sio.emit("joined_city", {"city": city}, to=sid)


async def emit_sensor_trust_update(city: str, payload: dict) -> None:
    try:
        await sio.emit("sensor_trust_update", payload, room=city.lower())
    except Exception:
        pass


async def emit_heatmap_update(city: str, payload: dict) -> None:
    try:
        await sio.emit("heatmap_update", payload, room=city.lower())
    except Exception:
        pass
