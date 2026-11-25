"""Sensor registration (one-time HMAC-SHA256 API key), listing, and trust history."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, success_response
from app.core.permissions import get_current_user
from app.core.security import generate_raw_api_key, hash_api_key
from app.database import get_db
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.models.user import User
from app.schemas.auth_schema import SensorRegisterRequest

router = APIRouter(prefix="/api/v1/sensors", tags=["Sensors"])


@router.post("/register", status_code=201)
async def register_sensor(
    payload: SensorRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a citizen/institutional/mobile sensor. Returns raw API key ONCE."""
    raw_key = generate_raw_api_key()
    key_hash = hash_api_key(raw_key)

    sensor = Sensor(
        owner_id=current_user.id,
        name=payload.name,
        city=payload.city.lower(),
        api_key_hash=key_hash,
        sensor_type=payload.sensor_type,
        status="active",
        model_meta=payload.model_meta,
        trust_weight=0.75,
        lat=payload.lat,
        lon=payload.lon,
    )
    db.add(sensor)

    # Auto-upgrade citizen to sensor_owner on first sensor registration
    if current_user.role == "citizen":
        current_user.role = "sensor_owner"

    await db.commit()
    await db.refresh(sensor)

    return success_response(
        {
            "sensor": {
                "id": str(sensor.id),
                "name": sensor.name,
                "city": sensor.city,
                "sensor_type": sensor.sensor_type,
                "status": sensor.status,
                "trust_weight": sensor.trust_weight,
                "lat": sensor.lat,
                "lon": sensor.lon,
                "model_meta": sensor.model_meta,
            },
            "api_key": raw_key,
            "api_key_notice": "Store this API key securely now. It is hashed with HMAC-SHA256 and cannot be retrieved again.",
        },
        status_code=201,
    )


@router.get("")
async def list_sensors(
    city: str = Query(default="chikkamagaluru"),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Sensor)
        .where(Sensor.city == city.lower())
        .order_by(desc(Sensor.trust_weight), Sensor.name)
    )
    sensors = res.scalars().all()
    return success_response(
        [
            {
                "id": str(s.id),
                "name": s.name,
                "city": s.city,
                "sensor_type": s.sensor_type,
                "status": s.status,
                "trust_weight": round(float(s.trust_weight), 4),
                "lat": s.lat,
                "lon": s.lon,
                "model_meta": s.model_meta,
                "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
            }
            for s in sensors
        ]
    )


@router.get("/{sensor_id}/trust-history")
async def sensor_trust_history(
    sensor_id: str,
    limit: int = Query(default=30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(sensor_id)
    except ValueError:
        raise AppError(400, "INVALID_SENSOR_ID", "Sensor ID must be a valid UUID.")

    sensor_res = await db.execute(select(Sensor).where(Sensor.id == sid))
    sensor = sensor_res.scalar_one_or_none()
    if not sensor:
        raise AppError(404, "SENSOR_NOT_FOUND", "Sensor not found.")

    logs_res = await db.execute(
        select(TrustLog)
        .where(TrustLog.sensor_id == sid)
        .order_by(desc(TrustLog.evaluated_at))
        .limit(limit)
    )
    logs = list(reversed(logs_res.scalars().all()))
    return success_response(
        {
            "sensor": {
                "id": str(sensor.id),
                "name": sensor.name,
                "sensor_type": sensor.sensor_type,
                "status": sensor.status,
                "trust_weight": round(float(sensor.trust_weight), 4),
                "model_meta": sensor.model_meta,
            },
            "history": [
                {
                    "reading_id": tl.reading_id,
                    "pm25_corrected": tl.pm25_corrected,
                    "prev_trust": tl.prev_trust,
                    "new_trust": tl.new_trust,
                    "agreement_score": tl.agreement_score,
                    "tier_used": tl.tier_used,
                    "reference_pm25": tl.reference_pm25,
                    "dist_ref_km": tl.dist_ref_km,
                    "evaluated_at": tl.evaluated_at.isoformat(),
                }
                for tl in logs
            ],
        }
    )


@router.patch("/{sensor_id}/revoke")
async def revoke_sensor(
    sensor_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(sensor_id)
    except ValueError:
        raise AppError(400, "INVALID_SENSOR_ID", "Sensor ID must be a valid UUID.")

    res = await db.execute(select(Sensor).where(Sensor.id == sid))
    sensor = res.scalar_one_or_none()
    if not sensor:
        raise AppError(404, "SENSOR_NOT_FOUND", "Sensor not found.")

    if current_user.role != "admin" and sensor.owner_id != current_user.id:
        raise AppError(403, "FORBIDDEN", "Only the sensor owner or an admin can revoke this sensor.")

    sensor.status = "revoked"
    await db.commit()
    return success_response({"id": str(sensor.id), "status": sensor.status})
