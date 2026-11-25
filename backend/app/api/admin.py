"""Admin endpoints (RBAC: admin only): official stations, fault injection, historical recompute, audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, success_response
from app.core.permissions import require_roles
from app.core.security import generate_raw_api_key, hash_api_key
from app.database import get_db
from app.engines.ingestion_engine import process_sensor_reading
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.models.user import AuditLog, User
from app.schemas.auth_schema import (
    FaultInjectionRequest,
    OfficialStationCreateRequest,
    RecomputeGridRequest,
)
from app.services.heatmap_service import compute_city_heatmap

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
admin_guard = require_roles("admin")


@router.post("/stations", status_code=201)
async def create_official_station(
    payload: OfficialStationCreateRequest,
    admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    raw_key = generate_raw_api_key()
    sensor = Sensor(
        owner_id=admin.id,
        name=payload.name,
        city=payload.city.lower(),
        api_key_hash=hash_api_key(raw_key),
        sensor_type="official",
        status="active",
        model_meta=payload.model_meta,
        trust_weight=1.0,
        lat=payload.lat,
        lon=payload.lon,
    )
    db.add(sensor)
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_email=admin.email,
            action="CREATE_OFFICIAL_STATION",
            target_type="sensor",
            details={"name": payload.name, "city": payload.city},
        )
    )
    await db.commit()
    await db.refresh(sensor)
    return success_response(
        {"id": str(sensor.id), "name": sensor.name, "trust_weight": 1.0, "api_key": raw_key},
        status_code=201,
    )


@router.post("/fault-injection")
async def inject_faulty_sensor(
    payload: FaultInjectionRequest,
    admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    """Live demo control: inject persistent +bias PM2.5 ticks to watch EWMA trust decay 0.75 -> 0.05."""
    sensor = None
    if payload.sensor_id:
        try:
            sid = uuid.UUID(payload.sensor_id)
        except ValueError:
            raise AppError(400, "INVALID_SENSOR_ID", "Invalid sensor UUID.")
        res = await db.execute(select(Sensor).where(Sensor.id == sid))
        sensor = res.scalar_one_or_none()
    else:
        res = await db.execute(
            select(Sensor)
            .where(
                Sensor.city == payload.city.lower(),
                Sensor.sensor_type != "official",
                Sensor.status != "revoked",
            )
            .order_by(desc(Sensor.trust_weight))
            .limit(1)
        )
        sensor = res.scalar_one_or_none()

    if not sensor:
        raise AppError(404, "NO_TARGET_SENSOR", "No non-official sensor available for fault injection.")

    # Determine baseline near official station
    base_pm25 = 28.0
    trajectory: list[dict] = []
    for tick in range(1, payload.ticks + 1):
        res_tick = await process_sensor_reading(
            db=db,
            sensor=sensor,
            pm25_raw=min(990.0, base_pm25 + payload.bias_pm25),
            rh_pct=payload.rh_pct,
            lat=sensor.lat,
            lon=sensor.lon,
            recorded_at=datetime.now(timezone.utc),
            broadcast=True,
        )
        trajectory.append(
            {
                "tick": tick,
                "pm25_raw": res_tick["pm25_raw"],
                "pm25_corrected": res_tick["pm25_corrected"],
                "new_trust": res_tick["new_trust"],
                "tier_used": res_tick["tier_used"],
                "status": res_tick["status"],
            }
        )

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_email=admin.email,
            action="INJECT_FAULTY_SENSOR",
            target_type="sensor",
            target_id=str(sensor.id),
            details={"bias_pm25": payload.bias_pm25, "ticks": payload.ticks, "final_trust": sensor.trust_weight},
        )
    )
    await db.commit()

    # Recompute and broadcast updated grid so connected UI sees false hotspot vanish
    grid = await compute_city_heatmap(
        db=db, city=sensor.city, mode="kriging", persist=True, broadcast=True
    )

    return success_response(
        {
            "sensor_id": str(sensor.id),
            "sensor_name": sensor.name,
            "final_trust": round(float(sensor.trust_weight), 4),
            "final_status": sensor.status,
            "trajectory": trajectory,
            "grid_compute_ms": grid["compute_ms"],
        }
    )


@router.post("/recompute")
async def recompute_heatmap(
    payload: RecomputeGridRequest,
    admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    """Constraint 3 proof: regenerate any historical or live grid directly from immutable raw_readings."""
    grid = await compute_city_heatmap(
        db=db,
        city=payload.city,
        mode=payload.mode,
        grid_size=payload.grid_size,
        at_timestamp=payload.timestamp,
        persist=True,
        broadcast=True,
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_email=admin.email,
            action="RECOMPUTE_GRID",
            target_type="aqi_grid",
            target_id=str(grid["grid_id"]),
            details={
                "city": payload.city,
                "mode_used": grid["mode_used"],
                "compute_ms": grid["compute_ms"],
                "source_timestamp": grid["source_timestamp"],
            },
        )
    )
    await db.commit()
    return success_response(grid)


@router.get("/trust-logs")
async def get_trust_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(TrustLog).order_by(desc(TrustLog.evaluated_at)).limit(limit))
    logs = res.scalars().all()
    return success_response(
        [
            {
                "id": tl.id,
                "sensor_id": str(tl.sensor_id),
                "reading_id": tl.reading_id,
                "pm25_corrected": tl.pm25_corrected,
                "prev_trust": tl.prev_trust,
                "new_trust": tl.new_trust,
                "agreement_score": tl.agreement_score,
                "tier_used": tl.tier_used,
                "evaluated_at": tl.evaluated_at.isoformat(),
            }
            for tl in logs
        ]
    )


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit))
    logs = res.scalars().all()
    return success_response(
        [
            {
                "id": a.id,
                "actor_email": a.actor_email,
                "action": a.action,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "details": a.details,
                "created_at": a.created_at.isoformat(),
            }
            for a in logs
        ]
    )


@router.get("/overview")
async def system_overview(
    _admin: User = Depends(admin_guard),
    db: AsyncSession = Depends(get_db),
):
    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    sensors_count = (await db.execute(select(func.count(Sensor.id)))).scalar_one()
    quarantined_count = (
        await db.execute(select(func.count(Sensor.id)).where(Sensor.status == "quarantined"))
    ).scalar_one()
    readings_count = (await db.execute(select(func.count(RawReading.id)))).scalar_one()
    return success_response(
        {
            "total_users": users_count,
            "total_sensors": sensors_count,
            "quarantined_sensors": quarantined_count,
            "immutable_raw_readings": readings_count,
        }
    )
