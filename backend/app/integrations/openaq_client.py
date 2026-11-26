"""Live OpenAQ v3 API client (api.openaq.org/v3) for official reference station fallback."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("vayumesh.openaq")

OPENAQ_V3_BASE = "https://api.openaq.org/v3"


async def fetch_openaq_nearest_pm25(
    lat: float = 13.3161,
    lon: float = 75.7720,
    radius_m: int = 25000,
) -> dict[str, Any] | None:
    """Query OpenAQ v3 for the nearest PM2.5 station within radius_m."""
    settings = get_settings()
    if not settings.OPENAQ_API_KEY:
        return None

    headers = {"X-API-Key": settings.OPENAQ_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            loc_resp = await client.get(
                f"{OPENAQ_V3_BASE}/locations",
                params={"coordinates": f"{lat},{lon}", "radius": radius_m, "limit": 5},
            )
            loc_resp.raise_for_status()
            locations = loc_resp.json().get("results", [])
            if not locations:
                return None

            loc = locations[0]
            loc_id = loc["id"]
            latest_resp = await client.get(f"{OPENAQ_V3_BASE}/locations/{loc_id}/latest")
            latest_resp.raise_for_status()
            latest = latest_resp.json().get("results", [])

            sensor_map = {s["id"]: s.get("parameter", {}).get("name") for s in loc.get("sensors", [])}
            pm25 = None
            pm10 = None
            for item in latest:
                pname = sensor_map.get(item.get("sensorsId"))
                if pname == "pm25" and item.get("value") is not None:
                    pm25 = float(item["value"])
                elif pname == "pm10" and item.get("value") is not None:
                    pm10 = float(item["value"])

            if pm25 is None:
                return None

            return {
                "source": "openaq_v3_live",
                "station": loc.get("name", "OpenAQ Station"),
                "pm25": pm25,
                "pm10": pm10,
                "last_update": latest[0].get("datetime", {}).get("utc") if latest else None,
            }
    except Exception as exc:
        logger.warning("OpenAQ v3 fetch failed: %s", exc)
        return None
