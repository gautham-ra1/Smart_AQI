"""High-resolution Satellite + Ground Heatmap Fusion, point lookup, mobile trails, and historical replay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.spatial.distance import cdist
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.aqi_engine import MAP_LAYER_LABEL, pm25_to_cpcb_subindex
from app.engines.humidity_correction import correct_pm25_humidity
from app.engines.kriging_engine import interpolate_aqi_grid
from app.integrations.openmeteo_client import fetch_cams_regional_grid
from app.models.aqi_grid import AQIGrid
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.realtime.socket_manager import emit_heatmap_update
from app.utils.geo_utils import (
    QUICK_ZONES,
    build_city_grid,
    haversine_km,
    latlon_to_local_km,
)


async def _fetch_mobile_trails(
    db: AsyncSession, mobile_sensors: list[Sensor], max_points: int = 25
) -> list[dict]:
    """Fetch recent GPS breadcrumb trails for mobile_fleet sensors from immutable raw_readings."""
    trails: list[dict] = []
    for s in mobile_sensors:
        res = await db.execute(
            select(RawReading)
            .where(RawReading.sensor_id == s.id)
            .order_by(desc(RawReading.recorded_at))
            .limit(max_points)
        )
        rows = list(reversed(res.scalars().all()))
        if len(rows) < 2:
            continue
        trails.append(
            {
                "sensor_id": str(s.id),
                "name": s.name,
                "vehicle": (s.model_meta or {}).get("vehicle", "Transit Vehicle"),
                "route": (s.model_meta or {}).get("route", "Chikkamagaluru Corridor"),
                "points": [
                    {
                        "lat": float(r.lat),
                        "lon": float(r.lon),
                        "pm25_raw": round(float(r.pm25_raw), 1),
                        "rh_pct": round(float(r.rh_pct), 1),
                        "recorded_at": r.recorded_at.isoformat(),
                    }
                    for r in rows
                ],
            }
        )
    return trails


async def compute_city_heatmap(
    db: AsyncSession,
    city: str = "chikkamagaluru",
    mode: str = "kriging",
    fusion_mode: str = "hybrid",
    grid_size: int = 80,
    at_timestamp: datetime | None = None,
    persist: bool = True,
    broadcast: bool = False,
) -> dict:
    """Compute a high-res 2D PM2.5 heatmap fusing ground/mobile sensors with Open-Meteo CAMS satellite prior.

    Args:
        mode: 'kriging' (Trust-Aware Ordinary Kriging) or 'idw' (Trust-Weighted IDW).
        fusion_mode: 'hybrid' (Satellite CAMS 5x5 prior + local ground/mobile override — zero empty pixels)
                     or 'ground_only' (ground/mobile sensors only; pixels >10 km from any sensor masked null).
    """
    city_key = city.lower()
    fusion_key = "ground_only" if fusion_mode == "ground_only" else "hybrid"
    grid_km, _, cfg = build_city_grid(city_key, grid_size=grid_size)
    target_ts = at_timestamp or datetime.now(timezone.utc)
    window_start = target_ts - timedelta(hours=12)

    sensors_res = await db.execute(
        select(Sensor).where(Sensor.city == city_key, Sensor.status != "revoked")
    )
    sensors = list(sensors_res.scalars().all())
    mobile_sensors = [s for s in sensors if s.sensor_type == "mobile_fleet"]

    lats: list[float] = []
    lons: list[float] = []
    vals: list[float] = []
    weights: list[float] = []
    is_official: list[bool] = []
    sensor_summaries: list[dict] = []

    for s in sensors:
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

        tl_res = await db.execute(select(TrustLog).where(TrustLog.reading_id == raw.id).limit(1))
        tl = tl_res.scalar_one_or_none()
        corrected_pm25 = (
            float(tl.pm25_corrected)
            if tl is not None
            else (
                float(raw.pm25_raw)
                if s.sensor_type == "official"
                else correct_pm25_humidity(raw.pm25_raw, raw.rh_pct)
            )
        )
        w = float(tl.new_trust) if tl is not None else float(s.trust_weight)
        tier_used = (
            tl.tier_used
            if tl is not None
            else ("official" if s.sensor_type == "official" else "reference_anchored")
        )

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
                "model_meta": s.model_meta or {},
                "recorded_at": raw.recorded_at.isoformat(),
            }
        )

    # Fetch 5x5 regional Open-Meteo CAMS satellite prior across Chikkamagaluru -> Sringeri
    cams_grid = await fetch_cams_regional_grid(
        min_lat=cfg["min_lat"],
        max_lat=cfg["max_lat"],
        min_lon=cfg["min_lon"],
        max_lon=cfg["max_lon"],
        dim=5,
    )

    ground_count = len(vals)
    ground_coords_km = (
        latlon_to_local_km(np.asarray(lats), np.asarray(lons), cfg["center_lat"], cfg["center_lon"])
        if ground_count > 0
        else np.empty((0, 2), dtype=np.float64)
    )

    # Fuse CAMS satellite prior anchors in unmonitored rural zones (>4.5 km from any trusted ground sensor)
    satellite_anchors_used = 0
    if fusion_key == "hybrid" or ground_count == 0:
        for anchor in cams_grid["anchors"]:
            near_trusted = False
            for idx in range(ground_count):
                if weights[idx] >= 0.35 and haversine_km(anchor["lat"], anchor["lon"], lats[idx], lons[idx]) <= 4.5:
                    near_trusted = True
                    break
            if not near_trusted:
                lats.append(anchor["lat"])
                lons.append(anchor["lon"])
                vals.append(anchor["pm25"])
                weights.append(0.18)  # Low weight -> local/mobile sensors always override when present
                is_official.append(False)
                satellite_anchors_used += 1

    coords_km = latlon_to_local_km(
        np.asarray(lats), np.asarray(lons), cfg["center_lat"], cfg["center_lon"]
    )
    # Use a wider spatial correlation range (12 km) across the 75 km Chikkamagaluru-Sringeri corridor
    interp = interpolate_aqi_grid(
        coords_km=coords_km,
        values=np.asarray(vals, dtype=np.float64),
        weights=np.asarray(weights, dtype=np.float64),
        is_official=np.asarray(is_official, dtype=bool),
        grid_pts_km=grid_km,
        mode=mode,
        vrange_km=12.0,
    )

    pred_flat = interp.pred_pm25.copy()
    std_flat = interp.std_dev.copy() if interp.std_dev is not None else None

    # In 'ground_only' mode, mask pixels > 9.5 km from any ground sensor as None (shows empty Sringeri pixels!)
    empty_pixels = 0
    total_pixels = grid_size * grid_size
    if fusion_key == "ground_only" and ground_count > 0:
        min_ground_dist = np.min(cdist(grid_km, ground_coords_km), axis=1)
        empty_mask = min_ground_dist > 9.5
        empty_pixels = int(np.sum(empty_mask))
        grid_2d = []
        std_2d = [] if std_flat is not None else None
        for r in range(grid_size):
            row_vals = []
            row_std = [] if std_flat is not None else None
            for c in range(grid_size):
                i = r * grid_size + c
                if empty_mask[i]:
                    row_vals.append(None)
                    if row_std is not None:
                        row_std.append(None)
                else:
                    row_vals.append(round(float(pred_flat[i]), 2))
                    if row_std is not None:
                        row_std.append(round(float(std_flat[i]), 2))
            grid_2d.append(row_vals)
            if std_2d is not None:
                std_2d.append(row_std)
        valid_preds = pred_flat[~empty_mask] if np.any(~empty_mask) else pred_flat
    else:
        grid_2d = np.round(pred_flat.reshape((grid_size, grid_size)), 2).tolist()
        std_2d = (
            np.round(std_flat.reshape((grid_size, grid_size)), 2).tolist()
            if std_flat is not None
            else None
        )
        valid_preds = pred_flat

    coverage_pct = round(100.0 * (total_pixels - empty_pixels) / total_pixels, 1)
    mean_pm25 = float(np.mean(valid_preds))
    max_pm25 = float(np.max(valid_preds))
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

    mobile_trails = await _fetch_mobile_trails(db, mobile_sensors)

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
            active_sensor_count=ground_count,
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
        "fusion_mode": fusion_key,
        "grid_size": grid_size,
        "bounds": bounds_dict,
        "quick_zones": QUICK_ZONES,
        "grid_pm25": grid_2d,
        "grid_std_dev": std_2d,
        "active_sensor_count": ground_count,
        "satellite_anchors_used": satellite_anchors_used,
        "coverage_pct": coverage_pct,
        "empty_pixels": empty_pixels,
        "compute_ms": interp.compute_ms,
        "summary": {
            "mean_pm25": round(mean_pm25, 2),
            "max_pm25": round(max_pm25, 2),
            "mean_aqi": mean_sub.aqi,
            "cpcb_band": mean_sub.band,
            "band_color": mean_sub.color,
        },
        "cams_prior": {
            "source": cams_grid["source"],
            "anchor_count": cams_grid["anchor_count"],
            "mean_pm25": cams_grid["mean_pm25"],
        },
        "sensors": sensor_summaries,
        "mobile_trails": mobile_trails,
        "source_timestamp": target_ts.isoformat(),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if broadcast:
        await emit_heatmap_update(city_key, payload)

    return payload


async def estimate_point_pm25(
    db: AsyncSession, lat: float, lon: float, city: str = "chikkamagaluru"
) -> dict:
    """Estimate hyperlocal PM2.5 at any clicked (lat, lon) in the Chikkamagaluru-Sringeri corridor."""
    grid = await compute_city_heatmap(
        db=db, city=city, mode="kriging", fusion_mode="hybrid", grid_size=60, persist=False, broadcast=False
    )
    b = grid["bounds"]
    rows = len(grid["grid_pm25"])
    cols = len(grid["grid_pm25"][0])
    row_frac = (b["max_lat"] - lat) / max(1e-6, b["max_lat"] - b["min_lat"])
    col_frac = (lon - b["min_lon"]) / max(1e-6, b["max_lon"] - b["min_lon"])
    r = max(0, min(rows - 1, int(round(row_frac * (rows - 1)))))
    c = max(0, min(cols - 1, int(round(col_frac * (cols - 1)))))
    pm25 = float(grid["grid_pm25"][r][c] or grid["cams_prior"]["mean_pm25"])
    std = float(grid["grid_std_dev"][r][c]) if grid["grid_std_dev"] and grid["grid_std_dev"][r][c] is not None else None
    sub = pm25_to_cpcb_subindex(pm25)

    # Determine dominant source at this point (nearest ground/mobile sensor vs satellite prior)
    nearest_dist = None
    nearest_name = None
    for s in grid["sensors"]:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if nearest_dist is None or d < nearest_dist:
            nearest_dist = d
            nearest_name = s["name"]

    data_source = (
        f"Local + Satellite Fusion (nearest: {nearest_name}, {nearest_dist:.1f} km)"
        if nearest_dist is not None and nearest_dist <= 8.0
        else f"Open-Meteo CAMS Satellite Prior (nearest ground sensor {nearest_dist:.1f} km away)"
        if nearest_dist is not None
        else "Open-Meteo CAMS Satellite Prior"
    )

    return {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "city": city,
        "pm25_equiv": round(pm25, 2),
        "uncertainty_std_dev": round(std, 2) if std is not None else None,
        "aqi_pm25_equiv": sub.aqi,
        "cpcb_band": sub.band,
        "band_color": sub.color,
        "mode_used": grid["mode_used"],
        "data_source": data_source,
        "layer_label": MAP_LAYER_LABEL,
    }
