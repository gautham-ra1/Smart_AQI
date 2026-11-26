"""Live CPCB Official Air Quality API client via api.data.gov.in.

Resource ID: 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 (Real-time Air Quality Index from various locations)
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("vayumesh.cpcb")

CPCB_RESOURCE_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"


async def fetch_cpcb_station_live(
    city: str = "Chikkamagaluru",
    state: str = "Karnataka",
) -> dict[str, Any] | None:
    """Fetch live PM2.5, PM10 & multi-pollutant data for an official KSPCB/CPCB station."""
    settings = get_settings()
    if not settings.DATA_GOV_API_KEY:
        return None

    params = {
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": 20,
        "filters[state]": state,
        "filters[city]": city,
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(CPCB_RESOURCE_URL, params=params)
            resp.raise_for_status()
            records = resp.json().get("records", [])

        city_lower = city.lower()
        matched = [
            r
            for r in records
            if city_lower in str(r.get("city", "")).lower()
            or "kalyana" in str(r.get("station", "")).lower()
            or "chikkamagaluru" in str(r.get("station", "")).lower()
        ]
        if not matched:
            return None

        pollutants: dict[str, float] = {}
        station_name = matched[0].get("station", "Kalyana Nagara - KSPCB")
        last_update = matched[0].get("last_update")

        for r in matched:
            pid = str(r.get("pollutant_id", "")).upper().replace(".", "")
            avg_val = r.get("pollutant_avg")
            if avg_val in (None, "", "NA", "N/A"):
                continue
            try:
                pollutants[pid] = float(avg_val)
            except ValueError:
                continue

        if "PM25" not in pollutants:
            return None

        return {
            "source": "cpcb_data_gov_live",
            "station": station_name,
            "pm25": pollutants["PM25"],
            "pm10": pollutants.get("PM10"),
            "no2": pollutants.get("NO2"),
            "so2": pollutants.get("SO2"),
            "co": pollutants.get("CO"),
            "ozone": pollutants.get("OZONE"),
            "last_update": last_update,
            "pollutants": pollutants,
        }
    except Exception as exc:
        logger.warning("CPCB data.gov.in fetch failed (%s): %s", type(exc).__name__, exc)
        return None
