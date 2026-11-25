"""Open-Meteo CAMS Air Quality API client (free, no-auth satellite/reanalysis background prior)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.utils.logger import get_logger

logger = get_logger("vayumesh.openmeteo")

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
_CACHE_TTL_SEC = 300.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


async def fetch_cams_prior(lat: float = 13.3161, lon: float = 75.7720) -> dict[str, Any]:
    """Fetch current CAMS PM2.5 / PM10 background prior from Open-Meteo.

    Falls back gracefully to a realistic Chikkamagaluru baseline if offline/unreachable.
    """
    cache_key = f"{lat:.2f}:{lon:.2f}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key][0]) < _CACHE_TTL_SEC:
        return _cache[cache_key][1]

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": "Asia/Kolkata",
    }
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(OPEN_METEO_AQ_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
            current = payload.get("current", {})
            data = {
                "source": "open-meteo-cams-live",
                "lat": lat,
                "lon": lon,
                "pm25": float(current.get("pm2_5") or 26.0),
                "pm10": float(current.get("pm10") or 42.0),
                "no2": current.get("nitrogen_dioxide"),
                "o3": current.get("ozone"),
                "co": current.get("carbon_monoxide"),
                "observed_at": current.get("time"),
            }
            _cache[cache_key] = (now, data)
            return data
    except Exception as exc:
        logger.warning("Open-Meteo CAMS unreachable (%s); using Chikkamagaluru baseline prior.", exc)
        fallback = {
            "source": "cams-baseline-fallback",
            "lat": lat,
            "lon": lon,
            "pm25": 26.5,
            "pm10": 44.0,
            "no2": 14.0,
            "o3": 38.0,
            "co": 240.0,
            "observed_at": None,
        }
        _cache[cache_key] = (now, fallback)
        return fallback
