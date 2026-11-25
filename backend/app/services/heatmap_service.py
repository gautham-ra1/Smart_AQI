"""Heatmap computation, point lookup, and historical replay from immutable raw_readings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.aqi_engine import MAP_LAYER_LABEL, pm25_to_cpcb_subindex
from app.engines.humidity_correction import correct_pm25_humidity
from app.engines.kriging_engine import interpolate_aqi_grid
from app.integrations.openmeteo_client import fetch_cams_prior
from app.models.aqi_grid import AQIGrid
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.realtime.socket_manager import emit_heatmap_update
from app.utils.geo_utils import build_city_grid, latlon_to_local_km


async def compute_city_heatmap(
    db: AsyncSession,
    city: str = "chikkamagaluru",
    mode: str = "kriging",
    grid_size: int = 50,
    at_timestamp: datetime | None = None,
    persist: bool = True,
    broadcast: bool = False,
) -> dict:
    """Compute a 2D interpolated PM2.5 heatmap for a city (live or historical replay at T)."""
    city_key = city.lower()
    grid_km, _, cfg = build_city_grid(city_key, grid_size=grid_size)
    target_ts = at_timestamp or datetime.now(timezone.utc)
    window_start = target_ts - timedelta(hours=6)

    sensors_res = await db.execute(
        select(Sensor).where(Sensor.city == city_key, Sensor.status != "revoked")
    )
    sensors = list(sensors_res.scalars().all())

    lats: list[float] = []
    lons: list[float] = []
    vals: list[float] = []
    weights: list[float] = []
    is_official: list[bool] = []
    sensor_summaries: list[dict] = []

    for s in sensors:
        # Query latest immutable raw_reading at or before target_ts
        raw_res = await db.execute(
            select(RawReading)
            .where(
                RawReading.sensor_id == s.id,
                RawReading.recorded_at <= target_ts,
                RawReading.recorded_at >= window_start,
            )
            .order_by(desc(RawReading.recorded_at))
            .limit(1)
        )
        raw = raw_res.scalar_one_or_none()
        if raw is None:
            continue

        # Look up matching TrustLog if present, else recompute RH-corrected value from immutable raw
        tl_res = await db.execute(
            select(TrustLog)
            .where(TrustLog.reading_id == raw.id)
            .limit(1)
        )
        tl = tl_res.scalar_one_or_none()
        corrected_pm25 = (
            float(tl.pm25_corrected)
            if tl is not None
            else (float(raw.pm25_raw) if s.sensor_type == "official" else correct_pm25_humidity(raw.pm25_raw, raw.rh_pct))
        )
        w = float(tl.new_trust) if tl is not None else float(s.trust_weight)
        tier_used = tl.tier_used if tl is not None else ("official" if s.sensor_type == "official" else "reference_anchored")

        lats.append(float(raw.lat))
        lons.append(float(raw.lon))
        vals.append(corrected_pm25)
        weights.append(w)
        is_official.append(s.sensor_type == "official")

        sub = pm25_to_cpcb_subindex(corrected_pm25)
        sensor_summaries.append(
            {
                "id": str(s.id),
                "name": s.name,
                "sensor_type": s.sensor_type,
                "status": s.status,
                "lat": float(raw.lat),
                "lon": float(raw.lon),
                "pm25_raw": round(float(raw.pm25_raw), 2),
                "pm25_corrected": round(corrected_pm25, 2),
                "rh_pct": round(float(raw.rh_pct), 1),
                "trust_weight": round(w, 4),
                "tier_used": tier_used,
                "aqi_pm25_equiv": sub.aqi,
                "cpcb_band": sub.band,
                "band_color": sub.color,
                "recorded_at": raw.recorded_at.isoformat(),
            }
        )

    # Always include Open-Meteo CAMS background prior if ground sensors are empty
    cams_prior = await fetch_cams_prior(cfg["center_lat"], cfg["center_lon"])
    if len(vals) == 0:
        lats = [cfg["center_lat"]]
        lons = [cfg["center_lon"]]
        vals = [cams_prior["pm25"]]
        weights = [0.50]
        is_official = [False]

    coords_km = latlon_to_local_km(
        np.asarray(lats), np.asarray(lons), cfg["center_lat"], cfg["center_lon"]
    )
    interp = interpolate_aqi_grid(
        coords_km=coords_km,
        values=np.asarray(vals, dtype=np.float64),
        weights=np.asarray(weights, dtype=np.float64),
        is_official=np.asarray(is_official, dtype=bool),
        grid_pts_km=grid_km,
        mode=mode,
    )

    grid_2d = np.round(interp.pred_pm25.reshape((grid_size, grid_size)), 2).tolist()
    std_2d = (
        np.round(interp.std_dev.reshape((grid_size, grid_size)), 2).tolist()
        if interp.std_dev is not None
        else None
    )

    mean_pm25 = float(np.mean(interp.pred_pm25))
    max_pm25 = float(np.max(interp.pred_pm25))
    mean_sub = pm25_to_cpcb_subindex(mean_pm25)

    bounds_dict = {
        "min_lat": cfg["min_lat"],
        "max_lat": cfg["max_lat"],
        "min_lon": cfg["min_lon"],
        "max_lon": cfg["max_lon"],
        "center_lat": cfg["center_lat"],
        "center_lon": cfg["center_lon"],
        "zoom": cfg["zoom"],
    }

    grid_id = None
    if persist:
        grid_row = AQIGrid(
            city=city_key,
            mode=interp.mode_used,
            requested_mode=interp.requested_mode,
            grid_size=grid_size,
            bounds=bounds_dict,
            grid_pm25=grid_2d,
            grid_std_dev=std_2d,
            active_sensor_count=len(sensor_summaries),
            compute_ms=interp.compute_ms,
            source_timestamp=target_ts,
            computed_at=datetime.now(timezone.utc),
        )
        db.add(grid_row)
        await db.commit()
        grid_id = grid_row.id

    payload = {
        "grid_id": grid_id,
        "city": city_key,
        "city_label": cfg["name"],
        "layer_label": MAP_LAYER_LABEL,
        "mode_used": interp.mode_used,
        "requested_mode": interp.requested_mode,
        "grid_size": grid_size,
        "bounds": bounds_dict,
        "grid_pm25": grid_2d,
        "grid_std_dev": std_2d,
        "active_sensor_count": len(sensor_summaries),
        "compute_ms": interp.compute_ms,
        "summary": {
            "mean_pm25": round(mean_pm25, 2),
            "max_pm25": round(max_pm25, 2),
            "mean_aqi": mean_sub.aqi,
            "cpcb_band": mean_sub.band,
            "band_color": mean_sub.color,
        },
        "cams_prior": cams_prior,
        "sensors": sensor_summaries,
        "source_timestamp": target_ts.isoformat(),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if broadcast:
        await emit_heatmap_update(city_key, payload)

    return payload


async def estimate_point_pm25(
    db: AsyncSession, lat: float, lon: float, city: str = "chikkamagaluru"
) -> dict:
    """Estimate hyperlocal PM2.5 at a single (lat, lon) coordinate using live sensors."""
    grid = await compute_city_heatmap(
        db=db, city=city, mode="kriging", grid_size=30, persist=False, broadcast=False
    )
    b = grid["bounds"]
    rows = len(grid["grid_pm25"])
    cols = len(grid["grid_pm25"][0])
    # Map lat/lon to nearest grid cell
    row_frac = (b["max_lat"] - lat) / max(1e-6, b["max_lat"] - b["min_lat"])
    col_frac = (lon - b["min_lon"]) / max(1e-6, b["max_lon"] - b["min_lon"])
    r = max(0, min(rows - 1, int(round(row_frac * (rows - 1)))))
    c = max(0, min(cols - 1, int(round(col_frac * (cols - 1)))))
    pm25 = float(grid["grid_pm25"][r][c])
    std = float(grid["grid_std_dev"][r][c]) if grid["grid_std_dev"] else None
    sub = pm25_to_cpcb_subindex(pm25)
    return {
        "lat": lat,
        "lon": lon,
        "city": city,
        "pm25_equiv": round(pm25, 2),
        "uncertainty_std_dev": round(std, 2) if std is not None else None,
        "aqi_pm25_equiv": sub.aqi,
        "cpcb_band": sub.band,
        "band_color": sub.color,
        "mode_used": grid["mode_used"],
        "layer_label": MAP_LAYER_LABEL,
    }
