"""Open-Meteo CAMS Air Quality API client (single-point + 5x5 regional satellite prior grid)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import numpy as np

from app.utils.logger import get_logger

logger = get_logger("vayumesh.openmeteo")

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
_CACHE_TTL_SEC = 600.0
_point_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_grid_cache: dict[str, tuple[float, dict[str, Any]]] = {}


async def fetch_cams_prior(lat: float = 13.3161, lon: float = 75.7720) -> dict[str, Any]:
    """Fetch current CAMS PM2.5 / PM10 background prior from Open-Meteo for a single point."""
    cache_key = f"{lat:.2f}:{lon:.2f}"
    now = time.time()
    if cache_key in _point_cache and (now - _point_cache[cache_key][0]) < _CACHE_TTL_SEC:
        return _point_cache[cache_key][1]

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": "Asia/Kolkata",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
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
            _point_cache[cache_key] = (now, data)
            return data
    except Exception as exc:
        logger.warning("Open-Meteo CAMS unreachable (%s); using Western Ghats baseline prior.", exc)
        fallback = {
            "source": "cams-baseline-fallback",
            "lat": lat,
            "lon": lon,
            "pm25": 24.5,
            "pm10": 40.0,
            "no2": 12.0,
            "o3": 36.0,
            "co": 220.0,
            "observed_at": None,
        }
        _point_cache[cache_key] = (now, fallback)
        return fallback


async def fetch_cams_regional_grid(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    dim: int = 5,
) -> dict[str, Any]:
    """Fetch a batched (dim x dim) satellite/reanalysis CAMS prior grid across Chikkamagaluru-Sringeri.

    Eliminates empty pixels in unmonitored Western Ghats taluks (Sringeri, Koppa, Balehonnur)
    while allowing trusted ground and mobile sensors to override within their spatial correlation radius.
    """
    cache_key = f"{min_lat:.3f}:{max_lat:.3f}:{min_lon:.3f}:{max_lon:.3f}:{dim}"
    now = time.time()
    if cache_key in _grid_cache and (now - _grid_cache[cache_key][0]) < _CACHE_TTL_SEC:
        return _grid_cache[cache_key][1]

    lats = np.linspace(min_lat + 0.015, max_lat - 0.015, dim)
    lons = np.linspace(min_lon + 0.015, max_lon - 0.015, dim)
    pts = [(round(float(la), 4), round(float(lo), 4)) for la in lats for lo in lons]

    params = {
        "latitude": ",".join(str(p[0]) for p in pts),
        "longitude": ",".join(str(p[1]) for p in pts),
        "current": "pm2_5,pm10",
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(OPEN_METEO_AQ_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
            items = payload if isinstance(payload, list) else [payload]

            anchors = []
            for idx, item in enumerate(items):
                la, lo = pts[idx]
                cur = item.get("current", {})
                pm25 = float(cur.get("pm2_5") if cur.get("pm2_5") is not None else 22.0)
                anchors.append({"lat": la, "lon": lo, "pm25": round(pm25, 2)})

            result = {
                "source": "open-meteo-cams-live",
                "anchor_count": len(anchors),
                "mean_pm25": round(float(np.mean([a["pm25"] for a in anchors])), 2),
                "anchors": anchors,
            }
            _grid_cache[cache_key] = (now, result)
            return result
    except Exception as exc:
        logger.warning("Open-Meteo regional grid fetch failed (%s); using topographic CAMS fallback.", exc)
        # Gentle Western Ghats east->west gradient (slightly cleaner in forested Sringeri hills)
        anchors = []
        for la, lo in pts:
            east_factor = max(0.0, (lo - min_lon) / max(1e-6, max_lon - min_lon))
            pm25 = round(18.5 + 8.5 * east_factor, 2)
            anchors.append({"lat": la, "lon": lo, "pm25": pm25})
        result = {
            "source": "cams-baseline-fallback",
            "anchor_count": len(anchors),
            "mean_pm25": round(float(np.mean([a["pm25"] for a in anchors])), 2),
            "anchors": anchors,
        }
        _grid_cache[cache_key] = (now, result)
        return result
