"""3-Tier Live Official Government Monitor Synchronizer (CPCB -> OpenAQ v3 -> Open-Meteo CAMS)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ingestion_engine import process_sensor_reading
from app.integrations.cpcb_client import fetch_cpcb_station_live
from app.integrations.openaq_client import fetch_openaq_nearest_pm25
from app.integrations.openmeteo_client import fetch_cams_prior
from app.models.sensor import Sensor


async def sync_official_stations_live(db: AsyncSession, city: str = "chikkamagaluru") -> list[dict]:
    """Fetch live government AQI telemetry for all official CAAQMS stations in the city."""
    res = await db.execute(
        select(Sensor).where(
            Sensor.city == city.lower(),
            Sensor.sensor_type == "official",
            Sensor.status != "revoked",
        )
    )
    stations = list(res.scalars().all())
    synced: list[dict] = []

    for st in stations:
        live = await fetch_cpcb_station_live(city="Chikkamagaluru", state="Karnataka")
        if live is None:
            live = await fetch_openaq_nearest_pm25(lat=st.lat, lon=st.lon)
        if live is None:
            cams = await fetch_cams_prior(lat=st.lat, lon=st.lon)
            live = {
                "source": cams["source"],
                "station": st.name,
                "pm25": cams["pm25"],
                "pm10": cams.get("pm10"),
                "pollutants": {"PM25": cams["pm25"], "PM10": cams.get("pm10"), "NO2": cams.get("no2"), "O3": cams.get("o3")},
                "last_update": cams.get("observed_at"),
            }

        meta = dict(st.model_meta or {})
        meta["live_source"] = live["source"]
        meta["last_live_sync"] = datetime.now(timezone.utc).isoformat()
        if live.get("pollutants"):
            meta["multi_pollutant_readings"] = live["pollutants"]
        st.model_meta = meta

        ingested = await process_sensor_reading(
            db=db,
            sensor=st,
            pm25_raw=float(live["pm25"]),
            pm10_raw=float(live["pm10"]) if live.get("pm10") is not None else None,
            rh_pct=65.0,
            lat=st.lat,
            lon=st.lon,
            broadcast=True,
        )
        ingested["live_source"] = live["source"]
        synced.append(ingested)

    return synced
