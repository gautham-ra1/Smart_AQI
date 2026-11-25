"""Citizen profile, personal sensors, and personal readings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import success_response
from app.core.permissions import get_current_user
from app.database import get_db
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.user import User
from app.schemas.auth_schema import ProfileUpdateRequest

router = APIRouter(prefix="/api/v1/citizens", tags=["Citizens"])


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return success_response(
        {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "health_profile": current_user.health_profile,
        }
    )


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.health_profile is not None:
        current_user.health_profile = payload.health_profile
    await db.commit()
    await db.refresh(current_user)
    return success_response(
        {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "health_profile": current_user.health_profile,
        }
    )


@router.get("/my-sensors")
async def my_sensors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Sensor)
        .where(Sensor.owner_id == current_user.id)
        .order_by(desc(Sensor.created_at))
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


@router.get("/my-readings")
async def my_readings(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sensor_ids_res = await db.execute(select(Sensor.id).where(Sensor.owner_id == current_user.id))
    sensor_ids = [row[0] for row in sensor_ids_res.all()]
    if not sensor_ids:
        return success_response([])

    res = await db.execute(
        select(RawReading)
        .where(RawReading.sensor_id.in_(sensor_ids))
        .order_by(desc(RawReading.recorded_at))
        .limit(min(limit, 200))
    )
    rows = res.scalars().all()
    return success_response(
        [
            {
                "id": r.id,
                "sensor_id": str(r.sensor_id),
                "pm25_raw": r.pm25_raw,
                "pm10_raw": r.pm10_raw,
                "rh_pct": r.rh_pct,
                "lat": r.lat,
                "lon": r.lon,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in rows
        ]
    )
