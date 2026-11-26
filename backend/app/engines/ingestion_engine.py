"""Core Ingestion Engine: immutable storage -> RH correction -> Two-Tier EWMA trust update."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.aqi_engine import pm25_to_cpcb_subindex
from app.engines.trust_engine import TIER1_RADIUS_KM, TrustEvaluation, update_sensor_trust
from app.integrations.openmeteo_client import fetch_cams_prior
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.realtime.socket_manager import emit_sensor_trust_update
from app.utils.geo_utils import haversine_km


async def _latest_corrected_by_sensor(
    db: AsyncSession,
    city: str,
    exclude_sensor_id,
    since_minutes: int = 120,
) -> tuple[list[tuple[Sensor, float]], list[tuple[Sensor, float]]]:
    """Return recent (official_nodes, peer_nodes) with their latest corrected PM2.5."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    sensors_res = await db.execute(
        select(Sensor).where(
            Sensor.city == city,
            Sensor.status != "revoked",
            Sensor.id != exclude_sensor_id,
        )
    )
    sensors = list(sensors_res.scalars().all())
    official_nodes: list[tuple[Sensor, float]] = []
    peer_nodes: list[tuple[Sensor, float]] = []

    for s in sensors:
        tl_res = await db.execute(
            select(TrustLog)
            .where(TrustLog.sensor_id == s.id, TrustLog.evaluated_at >= cutoff)
            .order_by(desc(TrustLog.evaluated_at))
            .limit(1)
        )
        tl = tl_res.scalar_one_or_none()
        if tl is None:
            continue
        if s.sensor_type == "official":
            official_nodes.append((s, float(tl.pm25_corrected)))
        elif s.trust_weight >= 0.35:
            peer_nodes.append((s, float(tl.pm25_corrected)))

    return official_nodes, peer_nodes


async def process_sensor_reading(
    db: AsyncSession,
    sensor: Sensor,
    pm25_raw: float,
    rh_pct: float,
    lat: float,
    lon: float,
    pm10_raw: float | None = None,
    temp_c: float | None = None,
    recorded_at: datetime | None = None,
    broadcast: bool = True,
) -> dict:
    """Persist immutable raw reading, compute RH-corrected Two-Tier trust, and log."""
    ts = recorded_at or datetime.now(timezone.utc)

    # 1. Append-only immutable raw reading insert (never mutated)
    raw = RawReading(
        sensor_id=sensor.id,
        pm25_raw=pm25_raw,
        pm10_raw=pm10_raw,
        rh_pct=rh_pct,
        temp_c=temp_c,
        lat=lat,
        lon=lon,
        recorded_at=ts,
    )
    db.add(raw)
    await db.flush()  # Obtain raw.id without committing yet

    # 2. Update sensor's live coordinates & heartbeat (supports mobile fleet GPS per tick)
    sensor.lat = lat
    sensor.lon = lon
    sensor.last_seen_at = ts

    # 3. Gather nearest official CAAQMS (<= 5 km) and peer nodes (<= 4 km)
    official_nodes, peer_nodes = await _latest_corrected_by_sensor(
        db, city=sensor.city, exclude_sensor_id=sensor.id
    )

    ref_pm25: float | None = None
    dist_ref_km: float | None = None
    if official_nodes:
        nearest_official = min(
            official_nodes,
            key=lambda item: haversine_km(lat, lon, item[0].lat, item[0].lon),
        )
        dist_ref_km = round(haversine_km(lat, lon, nearest_official[0].lat, nearest_official[0].lon), 3)
        ref_pm25 = nearest_official[1]

    peer_vals: list[float] = []
    if dist_ref_km is None or dist_ref_km > TIER1_RADIUS_KM:
        for peer_sensor, peer_pm25 in peer_nodes:
            if haversine_km(lat, lon, peer_sensor.lat, peer_sensor.lon) <= 4.0:
                peer_vals.append(peer_pm25)

    cams_prior_pm25: float | None = None
    if (dist_ref_km is None or dist_ref_km > TIER1_RADIUS_KM) and len(peer_vals) < 3 and sensor.sensor_type != "official":
        prior = await fetch_cams_prior(lat, lon)
        cams_prior_pm25 = prior["pm25"]

    # 4. Run Hygrometric Pre-Calibration + Two-Tier Adaptive EWMA Trust Engine
    eval_res: TrustEvaluation = update_sensor_trust(
        prev_trust=float(sensor.trust_weight),
        raw_pm25=pm25_raw,
        rh_pct=rh_pct,
        ref_pm25=ref_pm25,
        dist_ref_km=dist_ref_km,
        peer_vals=peer_vals,
        cams_prior_pm25=cams_prior_pm25,
        sensor_type=sensor.sensor_type,
    )

    sensor.trust_weight = eval_res.new_trust
    sensor.status = eval_res.status

    trust_log = TrustLog(
        sensor_id=sensor.id,
        reading_id=raw.id,
        pm25_corrected=eval_res.pm25_corrected,
        prev_trust=eval_res.prev_trust,
        new_trust=eval_res.new_trust,
        agreement_score=eval_res.agreement_score,
        tier_used=eval_res.tier_used,
        reference_pm25=ref_pm25,
        dist_ref_km=dist_ref_km,
        evaluated_at=ts,
    )
    db.add(trust_log)
    await db.commit()

    sub = pm25_to_cpcb_subindex(eval_res.pm25_corrected)
    result = {
        "reading_id": raw.id,
        "sensor_id": str(sensor.id),
        "sensor_name": sensor.name,
        "sensor_type": sensor.sensor_type,
        "city": sensor.city,
        "lat": lat,
        "lon": lon,
        "pm25_raw": pm25_raw,
        "pm25_corrected": eval_res.pm25_corrected,
        "rh_pct": rh_pct,
        "aqi_pm25_equiv": sub.aqi,
        "cpcb_band": sub.band,
        "prev_trust": eval_res.prev_trust,
        "new_trust": eval_res.new_trust,
        "agreement_score": eval_res.agreement_score,
        "tier_used": eval_res.tier_used,
        "status": eval_res.status,
        "dist_ref_km": dist_ref_km,
        "recorded_at": ts.isoformat(),
    }

    if broadcast:
        await emit_sensor_trust_update(sensor.city, result)

    return result
